"""
Vision Loop Demo Runner
-----------------------
Runs vision loop demonstrations with either:
1. Live desktop agent (real screenshots)
2. Pre-recorded screenshot sequences (for reliable demos)

This enables showing the vision loop working in demos without
requiring a real desktop agent connection.
"""

from __future__ import annotations

import asyncio
import logging
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


class DemoMode(str, Enum):
    """Mode for running the demo."""
    LIVE = "live"  # Real desktop agent
    RECORDED = "recorded"  # Pre-recorded screenshots
    SIMULATED = "simulated"  # Simulated responses without screenshots


@dataclass
class VisionDemoConfig:
    """Configuration for vision loop demo."""
    mode: DemoMode = DemoMode.SIMULATED
    task_description: str = "Find a car perfume on Amazon"
    person_id: Optional[str] = None
    screenshot_dir: Optional[str] = None  # For recorded mode
    max_steps: int = 10
    step_delay_ms: int = 1500  # Delay between steps for visibility
    on_step: Optional[Callable[[Dict[str, Any]], None]] = None  # Callback per step


@dataclass
class VisionDemoStep:
    """A step in the vision demo."""
    step_number: int
    screenshot_path: Optional[str]
    screen_analysis: Dict[str, Any]
    action_decision: Dict[str, Any]
    reasoning: str
    is_complete: bool = False


class VisionDemoRunner:
    """
    Runs vision loop demonstrations.

    For demos, this can operate in three modes:
    1. LIVE: Connects to actual desktop agent
    2. RECORDED: Uses pre-recorded screenshot sequences
    3. SIMULATED: Generates plausible responses without real screenshots
    """

    def __init__(self, config: VisionDemoConfig):
        self.config = config
        self.steps: List[VisionDemoStep] = []
        self.current_step = 0
        self._running = False

    async def run(self) -> List[VisionDemoStep]:
        """Run the vision demo and return all steps."""
        self._running = True
        self.steps = []
        self.current_step = 0

        LOGGER.info("[vision_demo] Starting demo: %s (mode=%s)",
                   self.config.task_description, self.config.mode.value)

        try:
            if self.config.mode == DemoMode.LIVE:
                return await self._run_live()
            elif self.config.mode == DemoMode.RECORDED:
                return await self._run_recorded()
            else:
                return await self._run_simulated()
        finally:
            self._running = False

    async def _run_live(self) -> List[VisionDemoStep]:
        """Run with live desktop agent."""
        from sakhi.apps.api.services.agent.vision_loop import VisionLoop
        from sakhi.apps.api.services.agent.sessions import (
            create_session,
            get_agents_for_person,
        )
        from sakhi.apps.api.services.agent.protocol import SessionRequest
        from sakhi.config.dev_persons import DEV_PERSONS

        # Use provided person_id or default to dev person "a"
        person_id = self.config.person_id or DEV_PERSONS["a"]["id"]

        # Get registered agents for this person
        agents = await get_agents_for_person(person_id)
        if not agents:
            raise ValueError("No registered desktop agent found. Please start the desktop agent first.")

        agent_id = agents[0].id
        LOGGER.info("[vision_demo] Using agent: %s", agent_id)

        # Create a session for this demo
        session = await create_session(
            person_id=person_id,
            agent_id=agent_id,
            request=SessionRequest(
                agent_id=agent_id,
                task_description=self.config.task_description,
            ),
        )
        session_id = session.id
        LOGGER.info("[vision_demo] Created session: %s", session_id)

        loop = VisionLoop(
            session_id=session_id,
            agent_id=agent_id,
            person_id=person_id,
            max_steps=self.config.max_steps,
            step_delay_ms=self.config.step_delay_ms,
        )

        # Hook into the loop to capture steps
        original_execute = loop._execute_step

        async def capture_step(*args, **kwargs):
            result = await original_execute(*args, **kwargs)
            step = VisionDemoStep(
                step_number=len(self.steps) + 1,
                screenshot_path=getattr(loop.state, 'last_screenshot_path', None),
                screen_analysis=loop.state.last_screen_analysis or {},
                action_decision=loop.state.last_action or {},
                reasoning=getattr(loop.state, 'last_reasoning', "") or "",
                is_complete=result.is_complete if hasattr(result, 'is_complete') else False,
            )
            self.steps.append(step)

            if self.config.on_step:
                self.config.on_step(step.__dict__)

            await asyncio.sleep(self.config.step_delay_ms / 1000)
            return result

        loop._execute_step = capture_step

        # Start the loop with the task description
        await loop.start(self.config.task_description)
        return self.steps

    async def _run_recorded(self) -> List[VisionDemoStep]:
        """Run with pre-recorded screenshots."""
        if not self.config.screenshot_dir:
            LOGGER.error("[vision_demo] screenshot_dir required for recorded mode")
            return []

        screenshot_dir = Path(self.config.screenshot_dir)
        if not screenshot_dir.exists():
            LOGGER.error("[vision_demo] Screenshot dir not found: %s", screenshot_dir)
            return []

        # Get ordered screenshots
        screenshots = sorted(screenshot_dir.glob("*.png"))
        if not screenshots:
            LOGGER.error("[vision_demo] No screenshots in: %s", screenshot_dir)
            return []

        from sakhi.apps.api.services.agent.screen_analyzer import analyze_screen
        from sakhi.apps.api.services.agent.action_decider import decide_next_action

        for i, screenshot in enumerate(screenshots[:self.config.max_steps]):
            self.current_step = i + 1

            # Analyze the screenshot
            analysis = await analyze_screen(
                screenshot_path=str(screenshot),
                width=1920,  # Assume standard resolution
                height=1080,
                task_context=self.config.task_description,
                previous_actions=[s.action_decision for s in self.steps[-3:]],
            )

            # Decide action
            decision = await decide_next_action(
                task_description=self.config.task_description,
                task_context={"preferences": await self._get_preferences()},
                screen_analysis=analysis,
                action_history=[s.action_decision for s in self.steps],
                step_number=self.current_step,
            )

            step = VisionDemoStep(
                step_number=self.current_step,
                screenshot_path=str(screenshot),
                screen_analysis=analysis,
                action_decision=decision.get("action", {}),
                reasoning=decision.get("reasoning", ""),
                is_complete=decision.get("is_complete", False),
            )
            self.steps.append(step)

            if self.config.on_step:
                self.config.on_step(step.__dict__)

            await asyncio.sleep(self.config.step_delay_ms / 1000)

            if step.is_complete:
                break

        return self.steps

    async def _run_simulated(self) -> List[VisionDemoStep]:
        """Run with simulated responses (no real screenshots)."""
        # Simulated demo sequence for "Find car perfume on Amazon"
        simulated_sequence = [
            {
                "analysis": {
                    "description": "Amazon homepage with search bar",
                    "page_type": "home",
                    "url": "https://www.amazon.com",
                    "elements": [
                        {"type": "input", "text": "Search Amazon", "x": 500, "y": 50, "actionable": True},
                        {"type": "link", "text": "Today's Deals", "x": 200, "y": 50, "actionable": True},
                    ],
                },
                "action": {"type": "click", "parameters": {"x": 500, "y": 50}, "description": "Click search bar"},
                "reasoning": "Need to search for car perfume. Clicking on the search bar to type query.",
            },
            {
                "analysis": {
                    "description": "Amazon search bar is focused, ready for input",
                    "page_type": "home",
                    "url": "https://www.amazon.com",
                    "elements": [
                        {"type": "input", "text": "", "x": 500, "y": 50, "actionable": True, "focused": True},
                    ],
                },
                "action": {"type": "type", "parameters": {"text": "car perfume woody scent"}, "description": "Type search query"},
                "reasoning": "User prefers woody scents (from preferences). Searching for 'car perfume woody scent'.",
            },
            {
                "analysis": {
                    "description": "Search bar with query typed, suggestions visible",
                    "page_type": "home",
                    "url": "https://www.amazon.com",
                    "elements": [
                        {"type": "button", "text": "Search", "x": 700, "y": 50, "actionable": True},
                        {"type": "text", "text": "car perfume woody scent", "x": 500, "y": 50},
                    ],
                },
                "action": {"type": "key", "parameters": {"key": "enter"}, "description": "Submit search"},
                "reasoning": "Search query is entered. Pressing Enter to search.",
            },
            {
                "analysis": {
                    "description": "Amazon search results for car perfume",
                    "page_type": "search_results",
                    "url": "https://www.amazon.com/s?k=car+perfume+woody+scent",
                    "elements": [
                        {"type": "link", "text": "Premium Car Air Freshener - Woody Cedar", "x": 400, "y": 300, "actionable": True, "relevance": "high"},
                        {"type": "text", "text": "4.5 out of 5 stars", "x": 400, "y": 340},
                        {"type": "text", "text": "$24.99", "x": 400, "y": 360},
                        {"type": "link", "text": "Car Perfume Sandalwood Musk", "x": 400, "y": 450, "actionable": True, "relevance": "high"},
                        {"type": "text", "text": "4.3 out of 5 stars", "x": 400, "y": 490},
                    ],
                },
                "action": {"type": "click", "parameters": {"x": 400, "y": 300}, "description": "Click first result"},
                "reasoning": "Found 'Premium Car Air Freshener - Woody Cedar'. This matches user's preference for woody scents (strong preference). Clicking to see details.",
            },
            {
                "analysis": {
                    "description": "Product detail page for woody car perfume",
                    "page_type": "product",
                    "url": "https://www.amazon.com/dp/B08XYZ123",
                    "text": "Premium Car Air Freshener - Woody Cedar. Natural essential oils. Long-lasting fragrance. 4.5 stars from 2,340 reviews. $24.99. Scent notes: Cedarwood, Sandalwood, hint of Citrus.",
                    "elements": [
                        {"type": "button", "text": "Add to Cart", "x": 900, "y": 400, "actionable": True},
                        {"type": "text", "text": "Premium Car Air Freshener - Woody Cedar", "x": 500, "y": 100},
                        {"type": "text", "text": "Scent: Cedarwood, Sandalwood, hint of Citrus", "x": 500, "y": 200},
                        {"type": "text", "text": "$24.99", "x": 900, "y": 200},
                    ],
                    "task_relevant": {
                        "found_target": True,
                        "next_suggested_action": "This product matches preferences well",
                    },
                },
                "action": None,
                "reasoning": "Found excellent match! 'Premium Car Air Freshener - Woody Cedar' with cedarwood and sandalwood (user loves woody scents), hint of citrus (user likes citrus). 4.5 stars with 2,340 reviews. Price: $24.99. This matches your scent preferences perfectly.",
                "is_complete": True,
            },
        ]

        preferences = await self._get_preferences()

        for i, step_data in enumerate(simulated_sequence[:self.config.max_steps]):
            self.current_step = i + 1

            step = VisionDemoStep(
                step_number=self.current_step,
                screenshot_path=None,  # Simulated - no screenshot
                screen_analysis=step_data["analysis"],
                action_decision=step_data.get("action", {}),
                reasoning=step_data["reasoning"],
                is_complete=step_data.get("is_complete", False),
            )
            self.steps.append(step)

            LOGGER.info("[vision_demo] Step %d: %s", self.current_step, step.reasoning[:50])

            if self.config.on_step:
                self.config.on_step(step.__dict__)

            await asyncio.sleep(self.config.step_delay_ms / 1000)

            if step.is_complete:
                break

        return self.steps

    async def _get_preferences(self) -> Dict[str, Any]:
        """Get user preferences for task context."""
        if not self.config.person_id:
            # Return demo preferences
            return {
                "scent": {
                    "loves": ["woody", "cedar", "sandalwood", "musk"],
                    "likes": ["citrus"],
                    "avoids": ["floral", "sweet"],
                },
                "style": "minimalist",
            }

        try:
            from sakhi.apps.api.services.memory.sensory_preferences import get_sensory_profile
            profile = await get_sensory_profile(self.config.person_id)
            return {
                "temperature": profile.temperature,
                "texture": profile.texture,
                "flavor": profile.flavor,
                "visual": profile.visual,
            }
        except Exception:
            return {}

    def stop(self) -> None:
        """Stop the demo."""
        self._running = False


async def run_vision_demo(
    task: str = "Find a car perfume on Amazon",
    mode: DemoMode = DemoMode.SIMULATED,
    person_id: Optional[str] = None,
    on_step: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to run a vision demo.

    Returns list of step dictionaries for easy JSON serialization.
    """
    config = VisionDemoConfig(
        mode=mode,
        task_description=task,
        person_id=person_id,
        on_step=on_step,
    )

    runner = VisionDemoRunner(config)
    steps = await runner.run()

    return [
        {
            "step": s.step_number,
            "screenshot": s.screenshot_path,
            "analysis": s.screen_analysis,
            "action": s.action_decision,
            "reasoning": s.reasoning,
            "complete": s.is_complete,
        }
        for s in steps
    ]


__all__ = [
    "VisionDemoConfig",
    "VisionDemoRunner",
    "VisionDemoStep",
    "DemoMode",
    "run_vision_demo",
]
