import axios from 'axios';

/** axios instance that sends Django's CSRF token on every POST. */
export const http = axios.create({
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

/** A message (Persian) for the student when a request failed. */
export function describeError(error) {
  if (error.response) return 'خطایی در ارتباط با سرور رخ داده، مجددا وارد شوید';
  if (error.request) return 'اتصال اینترنت خود را بررسی کنید.';
  return 'خطایی در ارتباط با سرور رخ داد. اتصال اینترنت خود را بررسی کنید.';
}
