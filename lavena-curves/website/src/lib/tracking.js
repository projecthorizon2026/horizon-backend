/**
 * Analytics & Tracking Utilities for Lumiere Curves
 *
 * Configure your tracking IDs:
 * - Google Analytics 4: Replace 'G-XXXXXXXXXX' in index.html
 * - Microsoft Clarity: Replace 'CLARITY_PROJECT_ID' in index.html
 * - Facebook Pixel: Replace 'FB_PIXEL_ID' in index.html
 *
 * To get these IDs:
 * 1. GA4: https://analytics.google.com → Create property → Get Measurement ID
 * 2. Clarity: https://clarity.microsoft.com → New project → Get project ID
 * 3. Facebook Pixel: https://business.facebook.com/events_manager → Create pixel
 */

// Check if tracking is available
const isTrackingEnabled = () => typeof window !== 'undefined' && window.gtag;

// Track page view
export const trackPageView = (pageName, pageUrl) => {
  if (isTrackingEnabled()) {
    window.gtag('event', 'page_view', {
      page_title: pageName,
      page_location: pageUrl || window.location.href
    });
  }

  // Track in Clarity
  if (window.clarity) {
    window.clarity('set', 'page', pageName);
  }

  // Track in Facebook
  if (window.fbq) {
    window.fbq('track', 'PageView');
  }
};

// Track product view
export const trackProductView = (product) => {
  if (!product) return;

  if (isTrackingEnabled()) {
    window.gtag('event', 'view_item', {
      currency: 'INR',
      value: product.price,
      items: [{
        item_id: product.sku || product.id,
        item_name: product.name,
        item_category: product.category,
        price: product.price,
        quantity: 1
      }]
    });
  }

  if (window.fbq) {
    window.fbq('track', 'ViewContent', {
      content_ids: [product.sku || product.id],
      content_name: product.name,
      content_category: product.category,
      content_type: 'product',
      value: product.price,
      currency: 'INR'
    });
  }
};

// Track add to cart
export const trackAddToCart = (product, quantity = 1) => {
  if (!product) return;

  if (isTrackingEnabled()) {
    window.gtag('event', 'add_to_cart', {
      currency: 'INR',
      value: product.price * quantity,
      items: [{
        item_id: product.sku || product.id,
        item_name: product.name,
        item_category: product.category,
        price: product.price,
        quantity: quantity
      }]
    });
  }

  if (window.fbq) {
    window.fbq('track', 'AddToCart', {
      content_ids: [product.sku || product.id],
      content_name: product.name,
      content_type: 'product',
      value: product.price * quantity,
      currency: 'INR'
    });
  }

  // Custom Clarity tag
  if (window.clarity) {
    window.clarity('set', 'cart_add', product.name);
  }
};

// Track remove from cart
export const trackRemoveFromCart = (product, quantity = 1) => {
  if (!product) return;

  if (isTrackingEnabled()) {
    window.gtag('event', 'remove_from_cart', {
      currency: 'INR',
      value: product.price * quantity,
      items: [{
        item_id: product.sku || product.id,
        item_name: product.name,
        price: product.price,
        quantity: quantity
      }]
    });
  }
};

// Track checkout initiation
export const trackBeginCheckout = (cartItems, total) => {
  if (!cartItems || !cartItems.length) return;

  const items = cartItems.map(item => ({
    item_id: item.sku || item.id,
    item_name: item.name,
    price: item.price,
    quantity: item.quantity
  }));

  if (isTrackingEnabled()) {
    window.gtag('event', 'begin_checkout', {
      currency: 'INR',
      value: total,
      items: items
    });
  }

  if (window.fbq) {
    window.fbq('track', 'InitiateCheckout', {
      content_ids: cartItems.map(i => i.sku || i.id),
      num_items: cartItems.length,
      value: total,
      currency: 'INR'
    });
  }

  if (window.clarity) {
    window.clarity('set', 'checkout', 'started');
  }
};

// Track shipping info added
export const trackAddShippingInfo = (total, shippingMethod) => {
  if (isTrackingEnabled()) {
    window.gtag('event', 'add_shipping_info', {
      currency: 'INR',
      value: total,
      shipping_tier: shippingMethod || 'standard'
    });
  }
};

// Track payment info added
export const trackAddPaymentInfo = (total, paymentMethod = 'razorpay') => {
  if (isTrackingEnabled()) {
    window.gtag('event', 'add_payment_info', {
      currency: 'INR',
      value: total,
      payment_type: paymentMethod
    });
  }

  if (window.fbq) {
    window.fbq('track', 'AddPaymentInfo', {
      value: total,
      currency: 'INR'
    });
  }
};

// Track purchase
export const trackPurchase = (orderDetails) => {
  if (!orderDetails) return;

  const items = orderDetails.items?.map(item => ({
    item_id: item.sku || item.id,
    item_name: item.name,
    price: item.price,
    quantity: item.quantity
  })) || [];

  if (isTrackingEnabled()) {
    window.gtag('event', 'purchase', {
      transaction_id: orderDetails.orderNumber || orderDetails.orderId,
      value: orderDetails.total,
      currency: 'INR',
      shipping: orderDetails.shippingCost || 0,
      items: items
    });
  }

  if (window.fbq) {
    window.fbq('track', 'Purchase', {
      content_ids: items.map(i => i.item_id),
      content_type: 'product',
      value: orderDetails.total,
      currency: 'INR',
      num_items: items.length
    });
  }

  if (window.clarity) {
    window.clarity('set', 'purchase', orderDetails.orderNumber || orderDetails.orderId);
    window.clarity('set', 'purchase_value', orderDetails.total);
  }
};

// Track search
export const trackSearch = (searchTerm) => {
  if (!searchTerm) return;

  if (isTrackingEnabled()) {
    window.gtag('event', 'search', {
      search_term: searchTerm
    });
  }

  if (window.fbq) {
    window.fbq('track', 'Search', {
      search_string: searchTerm
    });
  }
};

// Track signup/lead
export const trackSignup = (email, source = 'newsletter') => {
  if (isTrackingEnabled()) {
    window.gtag('event', 'sign_up', {
      method: source
    });

    window.gtag('event', 'generate_lead', {
      currency: 'INR',
      value: 0
    });
  }

  if (window.fbq) {
    window.fbq('track', 'Lead', {
      content_name: source
    });
  }
};

// Track custom events
export const trackCustomEvent = (eventName, params = {}) => {
  if (isTrackingEnabled()) {
    window.gtag('event', eventName, params);
  }

  if (window.clarity) {
    window.clarity('set', eventName, JSON.stringify(params));
  }
};

// Track scroll depth
export const trackScrollDepth = (percentage) => {
  if (isTrackingEnabled()) {
    window.gtag('event', 'scroll_depth', {
      percent_scrolled: percentage
    });
  }
};

// Track affiliate click
export const trackAffiliateClick = (affiliateCode) => {
  if (isTrackingEnabled()) {
    window.gtag('event', 'affiliate_click', {
      affiliate_code: affiliateCode
    });
  }

  if (window.clarity) {
    window.clarity('set', 'affiliate', affiliateCode);
  }
};

// Initialize tracking on page load
export const initTracking = () => {
  // Check for affiliate code in URL
  const urlParams = new URLSearchParams(window.location.search);
  const affiliateCode = urlParams.get('ref') || urlParams.get('affiliate');

  if (affiliateCode) {
    // Store affiliate code in session
    sessionStorage.setItem('affiliate_code', affiliateCode);
    trackAffiliateClick(affiliateCode);
  }

  // Track initial page view
  trackPageView(document.title);
};

// Export convenience methods for direct gtag access
export const gtag = (...args) => {
  if (isTrackingEnabled()) {
    window.gtag(...args);
  }
};

export default {
  trackPageView,
  trackProductView,
  trackAddToCart,
  trackRemoveFromCart,
  trackBeginCheckout,
  trackAddShippingInfo,
  trackAddPaymentInfo,
  trackPurchase,
  trackSearch,
  trackSignup,
  trackCustomEvent,
  trackScrollDepth,
  trackAffiliateClick,
  initTracking,
  gtag
};
