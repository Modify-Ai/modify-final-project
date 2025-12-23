import React, { ButtonHTMLAttributes, forwardRef } from 'react';
import { twMerge } from 'tailwind-merge';

// 1. Variant에 'destructive' 추가 (에러 해결)
export type ButtonVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'link' | 'destructive';

// 2. Size 타입 정의 추가 (에러 해결)
export type ButtonSize = 'default' | 'sm' | 'lg' | 'icon';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize; // size prop 추가
  isLoading?: boolean;
}

// 버튼 스타일 정의 함수 (색상/모양)
const getButtonClasses = (variant: ButtonVariant) => {
  switch (variant) {
    case 'default':
      return 'bg-purple-600 text-white hover:bg-purple-700 shadow-md border border-transparent';
    case 'secondary':
      return 'bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600 shadow-sm border border-transparent';
    case 'outline':
      return 'border border-purple-500 text-purple-600 hover:bg-purple-50 dark:border-purple-400 dark:text-purple-400 bg-transparent';
    case 'ghost':
      return 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 border border-transparent';
    case 'link':
      return 'text-purple-600 dark:text-purple-400 underline-offset-4 hover:underline border border-transparent p-0 h-auto';
    case 'destructive': // 빨간색 삭제 버튼 스타일 추가
      return 'bg-red-500 text-white hover:bg-red-600 dark:bg-red-900 dark:text-red-100 dark:hover:bg-red-900/90 shadow-sm border border-transparent';
    default:
      return 'bg-purple-600 text-white hover:bg-purple-700 shadow-md border border-transparent';
  }
};

// 3. 버튼 크기 정의 함수 추가
const getButtonSize = (size: ButtonSize) => {
  switch (size) {
    case 'sm':
      return 'h-9 px-3 rounded-md text-xs'; // 작은 버튼
    case 'lg':
      return 'h-11 px-8 rounded-md text-base'; // 큰 버튼
    case 'icon':
      return 'h-10 w-10 p-0 items-center justify-center'; // 아이콘 전용
    default:
      return 'h-10 px-4 py-2 rounded-lg text-sm'; // 기본
  }
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', isLoading, children, disabled, ...props }, ref) => {

    // 로딩 인디케이터
    const loadingSpinner = (
      <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75 fill-none stroke-current" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    );

    return (
      <button
        className={twMerge(
          // 공통 스타일
          'inline-flex items-center justify-center font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:pointer-events-none',
          // Variant (색상) 적용
          getButtonClasses(variant),
          // Size (크기) 적용
          getButtonSize(size),
          // 로딩 중이거나 비활성화 시 스타일
          (isLoading || disabled) && 'opacity-60 cursor-not-allowed',
          className
        )}
        ref={ref}
        disabled={isLoading || disabled}
        {...props}
      >
        {isLoading && loadingSpinner}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button };