"""
Personalized Product Search
---------------------------
Integrates browser automation with the preference engine for personalized results.

Flow:
1. User requests product search (e.g., "car perfume under $20")
2. Browser automation searches the website
3. Products are extracted from the page
4. Each product is scored against user's stored preferences
5. Results are returned sorted by preference match + review quality

Example:
    results = await personalized_product_search(
        person_id="user-123",
        query="car air freshener",
        budget=20.0,
        site="amazon",
    )
    # Returns products ranked by how well they match user's fragrance preferences
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from sakhi.apps.api.services.agent.browser_automation import (
    BrowserAutomation,
    ActionStrategy,
)
from sakhi.apps.api.services.memory.product_matching import (
    score_products_batch,
    get_preference_summary_for_domain,
)
from sakhi.apps.api.services.memory.preference_framework import (
    load_preferences,
    get_domain_summary,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Site Configurations
# =============================================================================

SITE_CONFIGS = {
    "amazon": {
        "url": "https://www.amazon.com",
        "search_selector": "input#twotabsearchtextbox",
        "product_extraction_js": """
            () => {
                const items = [];
                document.querySelectorAll('[data-asin]:not([data-asin=""])').forEach((item, i) => {
                    if (i >= 20) return;

                    // Title
                    const titleEl = item.querySelector('h2 span, .a-text-normal');
                    const title = titleEl ? titleEl.textContent.trim() : '';

                    // Price (handle multiple currencies)
                    const priceEl = item.querySelector('.a-price .a-offscreen');
                    let priceText = priceEl ? priceEl.textContent.trim() : '';

                    // Rating
                    const ratingEl = item.querySelector('.a-icon-alt');
                    let rating = null;
                    if (ratingEl) {
                        const match = ratingEl.textContent.match(/([0-9.]+)/);
                        if (match) rating = parseFloat(match[1]);
                    }

                    // Review count
                    const reviewEl = item.querySelector('.a-size-small .a-link-normal');
                    let reviews = 0;
                    if (reviewEl) {
                        const text = reviewEl.textContent.replace(/,/g, '');
                        const match = text.match(/([0-9]+)/);
                        if (match) reviews = parseInt(match[1]);
                    }

                    // Product link
                    const linkEl = item.querySelector('h2 a');
                    const link = linkEl ? linkEl.href : '';

                    // ASIN for later reference
                    const asin = item.getAttribute('data-asin');

                    // Description hints from various elements
                    const descEl = item.querySelector('.a-text-bold, .a-color-base');
                    const descHints = descEl ? descEl.textContent.trim() : '';

                    if (title.length > 15 && priceText) {
                        items.push({
                            title: title.substring(0, 150),
                            price_raw: priceText,
                            rating: rating,
                            reviews: reviews,
                            link: link,
                            asin: asin,
                            description: title + ' ' + descHints,
                        });
                    }
                });
                return items;
            }
        """,
    },
    "google_shopping": {
        "url": "https://www.google.com/shopping",
        "search_selector": "input[name='q']",
        "product_extraction_js": """
            () => {
                // Google Shopping specific extraction
                const items = [];
                document.querySelectorAll('[data-docid]').forEach((item, i) => {
                    if (i >= 20) return;
                    // ... similar extraction
                });
                return items;
            }
        """,
    },
}


# =============================================================================
# Price Parsing (Multi-Currency)
# =============================================================================

# Approximate conversion rates to USD
CURRENCY_TO_USD = {
    "USD": 1.0,
    "INR": 0.012,
    "EUR": 1.08,
    "GBP": 1.26,
    "CAD": 0.74,
    "AUD": 0.65,
}


def parse_price(price_text: str) -> tuple[Optional[float], str]:
    """
    Parse price from various currency formats.

    Returns:
        (amount_in_usd, original_currency)
    """
    if not price_text:
        return None, "USD"

    text = price_text.replace('\xa0', ' ').replace(',', '')

    # Detect currency
    currency = "USD"
    if "INR" in text or "₹" in text:
        currency = "INR"
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    elif "C$" in text or "CAD" in text:
        currency = "CAD"
    elif "A$" in text or "AUD" in text:
        currency = "AUD"

    # Extract numeric value
    match = re.search(r'[\d.]+', text)
    if not match:
        return None, currency

    amount = float(match.group())

    # Heuristic: large numbers without currency symbol are likely INR
    if currency == "USD" and amount > 100 and "$" not in text:
        currency = "INR"

    # Convert to USD
    usd_amount = amount * CURRENCY_TO_USD.get(currency, 1.0)

    return round(usd_amount, 2), currency


# =============================================================================
# Search Result Models
# =============================================================================

@dataclass
class ProductResult:
    """A single product result with preference matching."""
    title: str
    price_usd: float
    price_original: float
    currency: str
    rating: Optional[float]
    reviews: int
    link: str
    asin: Optional[str]
    description: str

    # Preference matching (populated after scoring)
    match_score: float = 0.5
    match_level: str = "unknown"
    match_reasons: List[str] = field(default_factory=list)
    match_warnings: List[str] = field(default_factory=list)

    # Computed scores
    review_score: float = 0.0  # rating * log(reviews)
    combined_score: float = 0.0  # preference + review weighted

    def compute_scores(self, preference_weight: float = 0.6) -> None:
        """Compute review score and combined score."""
        if self.rating and self.reviews:
            self.review_score = self.rating * math.log10(max(self.reviews, 1) + 1)

        # Combined score: weighted combination of preference match and review quality
        # Normalize review_score to 0-1 range (max realistic is ~20)
        normalized_review = min(self.review_score / 20.0, 1.0)

        self.combined_score = (
            preference_weight * self.match_score +
            (1 - preference_weight) * normalized_review
        )


@dataclass
class SearchResult:
    """Complete search result with personalization."""
    query: str
    budget: Optional[float]
    total_found: int
    budget_matches: List[ProductResult]
    premium_suggestions: List[ProductResult]
    preference_summary: Dict[str, Any]
    stats: Dict[str, Any]


# =============================================================================
# Main Search Function
# =============================================================================

async def personalized_product_search(
    person_id: str,
    query: str,
    budget: Optional[float] = None,
    premium_range: Optional[tuple[float, float]] = None,
    site: str = "amazon",
    max_results: int = 10,
    preference_weight: float = 0.6,
    headless: bool = True,
) -> SearchResult:
    """
    Search for products and rank by user's stored preferences.

    Args:
        person_id: User's ID for preference lookup
        query: Search query (e.g., "car air freshener")
        budget: Maximum price in USD
        premium_range: Optional (min, max) for premium suggestions above budget
        site: Which site to search ("amazon", "google_shopping")
        max_results: Maximum products to return per category
        preference_weight: How much to weight preferences vs reviews (0-1)
        headless: Run browser in headless mode

    Returns:
        SearchResult with budget matches and premium suggestions, ranked by preference match
    """
    LOGGER.info(
        "[personalized_search] Starting search for %s: '%s' (budget=$%s)",
        person_id[:8] if person_id else "?",
        query,
        budget,
    )

    # Get site configuration
    config = SITE_CONFIGS.get(site)
    if not config:
        raise ValueError(f"Unknown site: {site}. Supported: {list(SITE_CONFIGS.keys())}")

    # Set premium range defaults
    if budget and not premium_range:
        premium_range = (budget, budget * 2)

    # Get user's preference summary for context
    domain = _infer_domain(query)
    preference_summary = await get_preference_summary_for_domain(person_id, domain)

    # Search and extract products
    raw_products = await _search_and_extract(
        site_url=config["url"],
        search_selector=config["search_selector"],
        query=query,
        extraction_js=config["product_extraction_js"],
        headless=headless,
    )

    LOGGER.info("[personalized_search] Extracted %d raw products", len(raw_products))

    # Parse prices and create ProductResult objects
    products = []
    for p in raw_products:
        price_usd, currency = parse_price(p.get("price_raw", ""))
        if price_usd is None:
            continue

        products.append(ProductResult(
            title=p.get("title", ""),
            price_usd=price_usd,
            price_original=float(re.search(r'[\d.]+', p.get("price_raw", "0").replace(",", "")).group() or 0),
            currency=currency,
            rating=p.get("rating"),
            reviews=p.get("reviews", 0),
            link=p.get("link", ""),
            asin=p.get("asin"),
            description=p.get("description", p.get("title", "")),
        ))

    LOGGER.info("[personalized_search] %d products with valid prices", len(products))

    # Score products against preferences
    products_for_scoring = [
        {"name": p.title, "description": p.description}
        for p in products
    ]

    category = _infer_category(query)
    scored = await score_products_batch(person_id, products_for_scoring, category=category)

    # Merge scores back into products
    for i, product in enumerate(products):
        if i < len(scored):
            product.match_score = scored[i].get("match_score", 0.5)
            product.match_level = scored[i].get("match_level", "unknown")
            product.match_reasons = scored[i].get("match_reasons", [])
            product.match_warnings = scored[i].get("match_warnings", [])

        product.compute_scores(preference_weight)

    # Categorize by price
    budget_matches = []
    premium_suggestions = []

    for p in products:
        if budget and p.price_usd <= budget:
            budget_matches.append(p)
        elif premium_range and premium_range[0] < p.price_usd <= premium_range[1]:
            premium_suggestions.append(p)

    # Sort by combined score (preference + reviews)
    budget_matches.sort(key=lambda x: x.combined_score, reverse=True)
    premium_suggestions.sort(key=lambda x: x.combined_score, reverse=True)

    LOGGER.info(
        "[personalized_search] Results: %d in budget, %d premium",
        len(budget_matches),
        len(premium_suggestions),
    )

    return SearchResult(
        query=query,
        budget=budget,
        total_found=len(products),
        budget_matches=budget_matches[:max_results],
        premium_suggestions=premium_suggestions[:max_results],
        preference_summary=preference_summary,
        stats={
            "total_extracted": len(raw_products),
            "valid_prices": len(products),
            "budget_matches": len(budget_matches),
            "premium_options": len(premium_suggestions),
            "preference_weight": preference_weight,
            "domain": domain,
            "category": category,
        },
    )


async def _search_and_extract(
    site_url: str,
    search_selector: str,
    query: str,
    extraction_js: str,
    headless: bool = True,
) -> List[Dict[str, Any]]:
    """Execute browser search and extract products."""
    async with BrowserAutomation(
        headless=headless,
        strategy=ActionStrategy.DOM_FIRST,
    ) as browser:
        # Navigate to site
        await browser.navigate(site_url)
        await browser.wait(2000)

        # Search
        await browser.type_text(search_selector, query, press_enter=True)
        await browser.wait(4000)

        # Extract products
        products = await browser.page.evaluate(extraction_js)

        return products


def _infer_domain(query: str) -> str:
    """Infer preference domain from search query."""
    query_lower = query.lower()

    domain_keywords = {
        "fragrance": ["perfume", "cologne", "scent", "freshener", "fragrance", "aroma"],
        "food": ["food", "snack", "meal", "recipe", "ingredient", "restaurant"],
        "fashion": ["shirt", "dress", "shoes", "clothing", "outfit", "wear"],
        "travel": ["hotel", "resort", "vacation", "trip", "flight"],
        "wellness": ["supplement", "vitamin", "fitness", "health"],
    }

    for domain, keywords in domain_keywords.items():
        if any(kw in query_lower for kw in keywords):
            return domain

    return "custom"


def _infer_category(query: str) -> str:
    """Infer product category from search query."""
    query_lower = query.lower()

    # More specific category mapping
    if any(kw in query_lower for kw in ["car perfume", "car freshener", "air freshener"]):
        return "car_perfume"
    if any(kw in query_lower for kw in ["perfume", "cologne", "fragrance"]):
        return "perfume"
    if any(kw in query_lower for kw in ["restaurant", "food", "dining"]):
        return "restaurant"

    return "custom"


# =============================================================================
# High-Level Task Functions
# =============================================================================

async def search_with_preferences(
    person_id: str,
    query: str,
    budget: Optional[float] = None,
    explain_preferences: bool = True,
) -> Dict[str, Any]:
    """
    Search for products with full preference explanation.

    This is the main entry point for the API endpoint.
    """
    result = await personalized_product_search(
        person_id=person_id,
        query=query,
        budget=budget,
    )

    # Format for API response
    response = {
        "query": result.query,
        "budget": result.budget,
        "stats": result.stats,
        "budget_results": [
            _format_product(p, explain_preferences)
            for p in result.budget_matches
        ],
        "premium_suggestions": [
            _format_product(p, explain_preferences)
            for p in result.premium_suggestions
        ],
    }

    if explain_preferences:
        response["your_preferences"] = result.preference_summary

    return response


def _format_product(product: ProductResult, explain: bool) -> Dict[str, Any]:
    """Format a product for API response."""
    base = {
        "title": product.title,
        "price_usd": product.price_usd,
        "original_price": f"{product.currency} {product.price_original:,.0f}" if product.currency != "USD" else None,
        "rating": product.rating,
        "reviews": product.reviews,
        "link": product.link,
        "combined_score": round(product.combined_score, 3),
    }

    if explain:
        base["match"] = {
            "score": round(product.match_score, 3),
            "level": product.match_level,
            "reasons": product.match_reasons[:3],
            "warnings": product.match_warnings[:2],
        }

    return base


__all__ = [
    "personalized_product_search",
    "search_with_preferences",
    "SearchResult",
    "ProductResult",
]
