import React from 'react';
import { CategoryMegaMenu } from '../../../components/layout/CategoryMegaMenu';

export default function CategoryPage() {
  return (
    <div className="mx-auto h-[calc(100dvh-124px)] max-w-7xl overflow-y-auto overflow-x-hidden px-1 py-3 sm:px-2 md:h-[calc(100dvh-128px)] lg:h-auto lg:overflow-visible lg:px-4 lg:py-6">
      <CategoryMegaMenu />
    </div>
  );
}
