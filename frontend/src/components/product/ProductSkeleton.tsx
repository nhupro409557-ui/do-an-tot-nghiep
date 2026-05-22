import React from 'react';
import { motion } from 'motion/react';

export const ProductSkeleton = () => {
  return (
    <motion.div 
      initial={{ opacity: 0.5 }}
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      className="bg-white rounded-xl shadow-sm border border-gray-100 p-3 flex flex-col h-[320px]"
    >
      {/* Khung ảnh */}
      <div className="h-40 w-full shimmer-bg rounded-lg mb-4"></div>
      
      {/* Khung tiêu đề */}
      <div className="h-4 shimmer-bg rounded w-3/4 mb-2"></div>
      <div className="h-4 shimmer-bg rounded w-1/2 mb-4"></div>
      
      {/* Khung cấu hình */}
      <div className="h-12 shimmer-bg rounded-lg mb-4 opacity-50"></div>
      
      {/* Khung giá */}
      <div className="mt-auto flex gap-2">
        <div className="h-6 shimmer-bg rounded w-1/3"></div>
        <div className="h-6 shimmer-bg rounded w-1/4 opacity-50"></div>
      </div>
    </motion.div>
  );
};
