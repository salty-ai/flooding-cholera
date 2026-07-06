/* eslint-disable react-refresh/only-export-components */
import toast, { Toaster, type ToastOptions } from 'react-hot-toast';

const defaultOptions: ToastOptions = {
  duration: 4000,
  position: 'top-right',
};

export const showToast = {
  success: (message: string, options?: ToastOptions) =>
    toast.success(message, { ...defaultOptions, ...options }),

  error: (message: string, options?: ToastOptions) =>
    toast.error(message, { ...defaultOptions, duration: 5000, ...options }),

  info: (message: string, options?: ToastOptions) =>
    toast(message, {
      ...defaultOptions,
      ...options,
      icon: (
        <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
    }),

  warning: (message: string, options?: ToastOptions) =>
    toast(message, {
      ...defaultOptions,
      ...options,
      icon: (
        <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      ),
    }),

  loading: (message: string) => toast.loading(message, defaultOptions),

  dismiss: (toastId?: string) => toast.dismiss(toastId),

  promise: <T,>(
    promise: Promise<T>,
    messages: { loading: string; success: string; error: string }
  ) =>
    toast.promise(promise, messages, {
      ...defaultOptions,
      success: { duration: 3000 },
      error: { duration: 5000 },
    }),
};

export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      reverseOrder={false}
      gutter={8}
      containerClassName=""
      containerStyle={{}}
      toastOptions={{
        className: '',
        style: {
          background: '#fff',
          color: '#363636',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          borderRadius: '8px',
          padding: '12px 16px',
          fontSize: '14px',
        },
        success: {
          style: {
            background: '#f0fdf4',
            border: '1px solid #86efac',
          },
          iconTheme: {
            primary: '#22c55e',
            secondary: '#fff',
          },
        },
        error: {
          style: {
            background: '#fef2f2',
            border: '1px solid #fca5a5',
          },
          iconTheme: {
            primary: '#ef4444',
            secondary: '#fff',
          },
        },
      }}
    />
  );
}

export default ToastProvider;
