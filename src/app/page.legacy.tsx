'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import SalesEnablementChatUI from './home/page';
import Star_Landing_Page from './star-landing/star_landing_page';

export default function HomeLegacy() {
  const [showLanding, setShowLanding] = useState<boolean>(true);

  return (
    <div
      className="w-full h-full"
      style={{
        backgroundImage:
          "url(https://images.unsplash.com/photo-1503264116251-35a269479413?q=80&w=2069&auto=format&fit=crop)",
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      <AnimatePresence mode="wait">
        {showLanding && (
          <motion.div
            key="landing"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="overflow-y-auto w-full h-full"
          >
            <Star_Landing_Page />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
