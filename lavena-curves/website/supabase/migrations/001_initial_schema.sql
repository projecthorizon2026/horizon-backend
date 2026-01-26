-- ============================================
-- LUMIERE CURVES E-COMMERCE DATABASE SCHEMA
-- Enterprise-grade with analytics & multi-channel
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- CORE TABLES
-- ============================================

-- Admin Users
CREATE TABLE IF NOT EXISTS admins (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  role TEXT DEFAULT 'admin' CHECK (role IN ('super_admin', 'admin', 'staff')),
  name TEXT,
  avatar_url TEXT,
  last_login_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Products
CREATE TABLE IF NOT EXISTS products (
  id SERIAL PRIMARY KEY,
  sku TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  slug TEXT UNIQUE,
  description TEXT,
  short_description TEXT,
  price DECIMAL(10,2) NOT NULL,
  original_price DECIMAL(10,2),
  cost_price DECIMAL(10,2),
  category TEXT,
  subcategory TEXT,
  tags TEXT[],
  sizes TEXT[],
  colors JSONB DEFAULT '[]',
  in_stock BOOLEAN DEFAULT true,
  stock_quantity INTEGER DEFAULT 0,
  low_stock_threshold INTEGER DEFAULT 5,
  rating DECIMAL(2,1) DEFAULT 0,
  reviews_count INTEGER DEFAULT 0,
  badge TEXT,
  images TEXT[] DEFAULT '{}',
  video TEXT,
  features TEXT[] DEFAULT '{}',
  meta_title TEXT,
  meta_description TEXT,
  is_active BOOLEAN DEFAULT true,
  is_featured BOOLEAN DEFAULT false,
  weight_grams INTEGER,
  hsn_code TEXT,
  gst_rate DECIMAL(4,2) DEFAULT 12.00,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Product Variants (size/color combinations with individual stock)
CREATE TABLE IF NOT EXISTS product_variants (
  id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  size TEXT NOT NULL,
  color TEXT NOT NULL,
  color_hex TEXT,
  sku_variant TEXT UNIQUE,
  stock_quantity INTEGER DEFAULT 0,
  price_override DECIMAL(10,2),
  image_url TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, size, color)
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  phone TEXT,
  first_name TEXT,
  last_name TEXT,
  avatar_url TEXT,
  date_of_birth DATE,
  gender TEXT,
  addresses JSONB DEFAULT '[]',
  default_address_index INTEGER DEFAULT 0,
  total_orders INTEGER DEFAULT 0,
  total_spent DECIMAL(10,2) DEFAULT 0,
  average_order_value DECIMAL(10,2) DEFAULT 0,
  tags TEXT[] DEFAULT '{}',
  notes TEXT,
  accepts_marketing BOOLEAN DEFAULT true,
  marketing_opt_in_at TIMESTAMPTZ,
  first_order_at TIMESTAMPTZ,
  last_order_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY,
  order_number TEXT UNIQUE NOT NULL,
  customer_id INTEGER REFERENCES customers(id),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled', 'returned', 'refunded')),
  payment_status TEXT DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded', 'partially_refunded', 'cod')),
  payment_method TEXT DEFAULT 'razorpay',
  razorpay_order_id TEXT,
  razorpay_payment_id TEXT,
  razorpay_signature TEXT,
  subtotal DECIMAL(10,2) NOT NULL,
  shipping_cost DECIMAL(10,2) DEFAULT 0,
  tax_amount DECIMAL(10,2) DEFAULT 0,
  discount_amount DECIMAL(10,2) DEFAULT 0,
  discount_code TEXT,
  total DECIMAL(10,2) NOT NULL,
  currency TEXT DEFAULT 'INR',
  shipping_address JSONB NOT NULL,
  billing_address JSONB,
  customer_name TEXT,
  customer_email TEXT,
  customer_phone TEXT,
  notes TEXT,
  internal_notes TEXT,
  tracking_number TEXT,
  tracking_url TEXT,
  courier_name TEXT,
  estimated_delivery DATE,
  delivered_at TIMESTAMPTZ,
  source TEXT DEFAULT 'website' CHECK (source IN ('website', 'admin', 'amazon', 'flipkart', 'instagram', 'facebook', 'whatsapp', 'phone')),
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  affiliate_id INTEGER,
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Order Items
CREATE TABLE IF NOT EXISTS order_items (
  id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
  product_id INTEGER REFERENCES products(id),
  variant_id INTEGER REFERENCES product_variants(id),
  product_name TEXT NOT NULL,
  product_image TEXT,
  sku TEXT,
  size TEXT,
  color TEXT,
  quantity INTEGER NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  total_price DECIMAL(10,2) NOT NULL,
  tax_rate DECIMAL(4,2) DEFAULT 0,
  tax_amount DECIMAL(10,2) DEFAULT 0,
  discount_amount DECIMAL(10,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Order Status History
CREATE TABLE IF NOT EXISTS order_status_history (
  id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  notes TEXT,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inventory Transactions
CREATE TABLE IF NOT EXISTS inventory_transactions (
  id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id),
  variant_id INTEGER REFERENCES product_variants(id),
  type TEXT NOT NULL CHECK (type IN ('purchase', 'sale', 'adjustment', 'return', 'damage', 'transfer', 'sync')),
  quantity_change INTEGER NOT NULL,
  quantity_before INTEGER,
  quantity_after INTEGER,
  reference_type TEXT,
  reference_id TEXT,
  notes TEXT,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- MARKETING & DISCOUNTS
-- ============================================

-- Discount Codes
CREATE TABLE IF NOT EXISTS discount_codes (
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  description TEXT,
  type TEXT NOT NULL CHECK (type IN ('percentage', 'fixed', 'free_shipping', 'buy_x_get_y')),
  value DECIMAL(10,2) NOT NULL,
  min_order_value DECIMAL(10,2) DEFAULT 0,
  max_discount_amount DECIMAL(10,2),
  max_uses INTEGER,
  max_uses_per_customer INTEGER DEFAULT 1,
  used_count INTEGER DEFAULT 0,
  applicable_products INTEGER[],
  applicable_categories TEXT[],
  valid_from TIMESTAMPTZ DEFAULT NOW(),
  valid_until TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Discount Usage Log
CREATE TABLE IF NOT EXISTS discount_usage (
  id SERIAL PRIMARY KEY,
  discount_id INTEGER REFERENCES discount_codes(id),
  order_id INTEGER REFERENCES orders(id),
  customer_id INTEGER REFERENCES customers(id),
  discount_amount DECIMAL(10,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ANALYTICS & TRACKING
-- ============================================

-- Visitor Sessions
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  visitor_id TEXT NOT NULL,
  customer_id INTEGER REFERENCES customers(id),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,
  page_views INTEGER DEFAULT 0,
  device_type TEXT,
  browser TEXT,
  browser_version TEXT,
  os TEXT,
  os_version TEXT,
  screen_width INTEGER,
  screen_height INTEGER,
  viewport_width INTEGER,
  viewport_height INTEGER,
  referrer TEXT,
  referrer_domain TEXT,
  landing_page TEXT,
  exit_page TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  utm_term TEXT,
  utm_content TEXT,
  country TEXT,
  region TEXT,
  city TEXT,
  ip_address TEXT,
  is_bot BOOLEAN DEFAULT false,
  is_converted BOOLEAN DEFAULT false,
  conversion_value DECIMAL(10,2),
  conversion_order_id INTEGER
);

-- Page Events (Granular tracking)
CREATE TABLE IF NOT EXISTS page_events (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  visitor_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  page_url TEXT,
  page_path TEXT,
  page_title TEXT,
  element_id TEXT,
  element_class TEXT,
  element_tag TEXT,
  element_text TEXT,
  scroll_depth INTEGER,
  time_on_page INTEGER,
  product_id INTEGER,
  product_name TEXT,
  product_price DECIMAL(10,2),
  product_category TEXT,
  cart_value DECIMAL(10,2),
  quantity INTEGER,
  search_query TEXT,
  metadata JSONB DEFAULT '{}',
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_page_events_session ON page_events(session_id);
CREATE INDEX IF NOT EXISTS idx_page_events_visitor ON page_events(visitor_id);
CREATE INDEX IF NOT EXISTS idx_page_events_type ON page_events(event_type);
CREATE INDEX IF NOT EXISTS idx_page_events_timestamp ON page_events(timestamp);

-- Cart Abandonment
CREATE TABLE IF NOT EXISTS abandoned_carts (
  id SERIAL PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  visitor_id TEXT NOT NULL,
  customer_id INTEGER REFERENCES customers(id),
  email TEXT,
  phone TEXT,
  cart_items JSONB NOT NULL,
  cart_value DECIMAL(10,2),
  abandoned_at_step TEXT CHECK (abandoned_at_step IN ('cart', 'info', 'shipping', 'payment')),
  recovery_email_1_sent BOOLEAN DEFAULT false,
  recovery_email_1_at TIMESTAMPTZ,
  recovery_email_2_sent BOOLEAN DEFAULT false,
  recovery_email_2_at TIMESTAMPTZ,
  recovery_sms_sent BOOLEAN DEFAULT false,
  recovery_sms_at TIMESTAMPTZ,
  recovered BOOLEAN DEFAULT false,
  recovered_order_id INTEGER REFERENCES orders(id),
  recovered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- AFFILIATE MARKETING
-- ============================================

-- Affiliates
CREATE TABLE IF NOT EXISTS affiliates (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  phone TEXT,
  affiliate_code TEXT UNIQUE NOT NULL,
  commission_type TEXT DEFAULT 'percentage' CHECK (commission_type IN ('percentage', 'fixed')),
  commission_value DECIMAL(10,2) DEFAULT 10,
  cookie_duration_days INTEGER DEFAULT 30,
  payment_method TEXT,
  payment_details JSONB,
  total_clicks INTEGER DEFAULT 0,
  total_conversions INTEGER DEFAULT 0,
  total_revenue DECIMAL(10,2) DEFAULT 0,
  total_commission_earned DECIMAL(10,2) DEFAULT 0,
  total_commission_paid DECIMAL(10,2) DEFAULT 0,
  pending_commission DECIMAL(10,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Affiliate Events
CREATE TABLE IF NOT EXISTS affiliate_events (
  id SERIAL PRIMARY KEY,
  affiliate_id INTEGER REFERENCES affiliates(id),
  event_type TEXT NOT NULL CHECK (event_type IN ('click', 'conversion', 'commission_paid')),
  session_id UUID REFERENCES sessions(id),
  order_id INTEGER REFERENCES orders(id),
  order_value DECIMAL(10,2),
  commission_amount DECIMAL(10,2),
  ip_address TEXT,
  user_agent TEXT,
  referrer TEXT,
  landing_page TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- MARKETPLACE & SOCIAL COMMERCE
-- ============================================

-- Marketplace Connections
CREATE TABLE IF NOT EXISTS marketplace_connections (
  id SERIAL PRIMARY KEY,
  marketplace TEXT NOT NULL CHECK (marketplace IN ('amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'instagram', 'facebook', 'pinterest', 'google_shopping')),
  display_name TEXT,
  seller_id TEXT,
  store_id TEXT,
  api_credentials JSONB,
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMPTZ,
  sync_inventory BOOLEAN DEFAULT true,
  sync_orders BOOLEAN DEFAULT true,
  sync_prices BOOLEAN DEFAULT true,
  sync_frequency_minutes INTEGER DEFAULT 30,
  last_inventory_sync TIMESTAMPTZ,
  last_orders_sync TIMESTAMPTZ,
  sync_status TEXT DEFAULT 'pending',
  sync_error TEXT,
  is_active BOOLEAN DEFAULT true,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Marketplace Product Listings
CREATE TABLE IF NOT EXISTS marketplace_listings (
  id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  marketplace_connection_id INTEGER REFERENCES marketplace_connections(id),
  marketplace TEXT NOT NULL,
  marketplace_product_id TEXT,
  marketplace_sku TEXT,
  listing_url TEXT,
  marketplace_price DECIMAL(10,2),
  marketplace_stock INTEGER,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'inactive', 'suppressed', 'error')),
  status_reason TEXT,
  last_sync_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, marketplace_connection_id)
);

-- Marketplace Orders
CREATE TABLE IF NOT EXISTS marketplace_orders (
  id SERIAL PRIMARY KEY,
  marketplace TEXT NOT NULL,
  marketplace_connection_id INTEGER REFERENCES marketplace_connections(id),
  marketplace_order_id TEXT NOT NULL,
  order_id INTEGER REFERENCES orders(id),
  marketplace_status TEXT,
  buyer_name TEXT,
  buyer_email TEXT,
  buyer_phone TEXT,
  shipping_address JSONB,
  items JSONB,
  subtotal DECIMAL(10,2),
  marketplace_fee DECIMAL(10,2),
  shipping_cost DECIMAL(10,2),
  tax_amount DECIMAL(10,2),
  total DECIMAL(10,2),
  net_amount DECIMAL(10,2),
  currency TEXT DEFAULT 'INR',
  tracking_number TEXT,
  shipped_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  marketplace_created_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(marketplace, marketplace_order_id)
);

-- Social Commerce Catalog
CREATE TABLE IF NOT EXISTS social_catalog (
  id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('instagram', 'facebook', 'pinterest', 'google_shopping')),
  platform_product_id TEXT,
  catalog_id TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'error')),
  rejection_reason TEXT,
  availability TEXT DEFAULT 'in stock',
  last_sync_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, platform)
);

-- ============================================
-- SEO & CONTENT
-- ============================================

-- SEO Keywords Tracking
CREATE TABLE IF NOT EXISTS seo_keywords (
  id SERIAL PRIMARY KEY,
  keyword TEXT NOT NULL,
  search_volume INTEGER,
  keyword_difficulty INTEGER,
  cpc DECIMAL(10,2),
  current_position INTEGER,
  previous_position INTEGER,
  position_change INTEGER,
  target_url TEXT,
  target_product_id INTEGER REFERENCES products(id),
  clicks_last_7d INTEGER DEFAULT 0,
  clicks_last_30d INTEGER DEFAULT 0,
  impressions_last_7d INTEGER DEFAULT 0,
  impressions_last_30d INTEGER DEFAULT 0,
  ctr DECIMAL(5,2),
  source TEXT DEFAULT 'manual',
  is_tracking BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- EMAIL MARKETING
-- ============================================

-- Email Templates
CREATE TABLE IF NOT EXISTS email_templates (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('transactional', 'marketing', 'automation')),
  subject TEXT NOT NULL,
  preview_text TEXT,
  html_content TEXT,
  text_content TEXT,
  variables JSONB DEFAULT '[]',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email Campaigns
CREATE TABLE IF NOT EXISTS email_campaigns (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT CHECK (type IN ('newsletter', 'promotion', 'abandoned_cart', 'welcome', 'win_back', 'product_launch')),
  template_id INTEGER REFERENCES email_templates(id),
  subject TEXT,
  preview_text TEXT,
  content TEXT,
  segment_criteria JSONB,
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  total_recipients INTEGER DEFAULT 0,
  total_sent INTEGER DEFAULT 0,
  total_delivered INTEGER DEFAULT 0,
  total_bounced INTEGER DEFAULT 0,
  total_opened INTEGER DEFAULT 0,
  unique_opens INTEGER DEFAULT 0,
  total_clicked INTEGER DEFAULT 0,
  unique_clicks INTEGER DEFAULT 0,
  total_unsubscribed INTEGER DEFAULT 0,
  total_converted INTEGER DEFAULT 0,
  revenue_generated DECIMAL(10,2) DEFAULT 0,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'sending', 'sent', 'cancelled')),
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email Campaign Recipients
CREATE TABLE IF NOT EXISTS email_recipients (
  id SERIAL PRIMARY KEY,
  campaign_id INTEGER REFERENCES email_campaigns(id) ON DELETE CASCADE,
  customer_id INTEGER REFERENCES customers(id),
  email TEXT NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'bounced', 'opened', 'clicked', 'unsubscribed', 'converted')),
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  converted_at TIMESTAMPTZ,
  converted_order_id INTEGER REFERENCES orders(id),
  unsubscribed_at TIMESTAMPTZ
);

-- ============================================
-- CUSTOMER SEGMENTS
-- ============================================

-- Customer Segments
CREATE TABLE IF NOT EXISTS customer_segments (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  criteria JSONB NOT NULL,
  customer_count INTEGER DEFAULT 0,
  is_dynamic BOOLEAN DEFAULT true,
  last_computed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Segment Membership (for static segments)
CREATE TABLE IF NOT EXISTS segment_members (
  id SERIAL PRIMARY KEY,
  segment_id INTEGER REFERENCES customer_segments(id) ON DELETE CASCADE,
  customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(segment_id, customer_id)
);

-- ============================================
-- DROPSHIPPING
-- ============================================

-- Dropship Suppliers
CREATE TABLE IF NOT EXISTS dropship_suppliers (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  code TEXT UNIQUE NOT NULL,
  contact_name TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  website TEXT,
  api_endpoint TEXT,
  api_key TEXT,
  api_secret TEXT,
  webhook_url TEXT,
  auto_fulfill BOOLEAN DEFAULT false,
  fulfillment_time_days INTEGER DEFAULT 3,
  shipping_methods JSONB DEFAULT '[]',
  return_policy TEXT,
  is_active BOOLEAN DEFAULT true,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dropship Product Mappings
CREATE TABLE IF NOT EXISTS dropship_products (
  id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  supplier_id INTEGER REFERENCES dropship_suppliers(id),
  supplier_product_id TEXT,
  supplier_sku TEXT,
  supplier_price DECIMAL(10,2),
  supplier_stock INTEGER,
  auto_sync_stock BOOLEAN DEFAULT true,
  auto_sync_price BOOLEAN DEFAULT false,
  markup_type TEXT DEFAULT 'percentage' CHECK (markup_type IN ('percentage', 'fixed')),
  markup_value DECIMAL(10,2) DEFAULT 50,
  last_sync_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, supplier_id)
);

-- Dropship Orders
CREATE TABLE IF NOT EXISTS dropship_orders (
  id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(id),
  order_item_id INTEGER REFERENCES order_items(id),
  supplier_id INTEGER REFERENCES dropship_suppliers(id),
  supplier_order_id TEXT,
  supplier_status TEXT,
  cost_price DECIMAL(10,2),
  shipping_cost DECIMAL(10,2),
  total_cost DECIMAL(10,2),
  tracking_number TEXT,
  tracking_url TEXT,
  submitted_at TIMESTAMPTZ,
  confirmed_at TIMESTAMPTZ,
  shipped_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- STORE SETTINGS
-- ============================================

-- Store Settings (key-value)
CREATE TABLE IF NOT EXISTS store_settings (
  id SERIAL PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value JSONB,
  description TEXT,
  updated_by UUID REFERENCES admins(id),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default settings
INSERT INTO store_settings (key, value, description) VALUES
  ('store_name', '"Lumière Curves"', 'Store display name'),
  ('store_email', '"hello@lumierecurves.shop"', 'Primary contact email'),
  ('store_phone', '"+971509751546"', 'Primary contact phone'),
  ('store_address', '{"city": "Mumbai", "state": "Maharashtra", "country": "India"}', 'Store address'),
  ('currency', '"INR"', 'Default currency'),
  ('tax_rate', '12', 'Default GST rate'),
  ('free_shipping_threshold', '2000', 'Minimum order for free shipping'),
  ('default_shipping_cost', '99', 'Default shipping cost'),
  ('order_prefix', '"LC"', 'Order number prefix'),
  ('low_stock_threshold', '5', 'Default low stock alert threshold')
ON CONFLICT (key) DO NOTHING;

-- ============================================
-- REVIEWS & RATINGS
-- ============================================

-- Product Reviews
CREATE TABLE IF NOT EXISTS product_reviews (
  id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  customer_id INTEGER REFERENCES customers(id),
  order_id INTEGER REFERENCES orders(id),
  rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
  title TEXT,
  content TEXT,
  pros TEXT[],
  cons TEXT[],
  images TEXT[],
  is_verified_purchase BOOLEAN DEFAULT false,
  is_approved BOOLEAN DEFAULT false,
  is_featured BOOLEAN DEFAULT false,
  helpful_count INTEGER DEFAULT 0,
  reported_count INTEGER DEFAULT 0,
  admin_response TEXT,
  admin_responded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);

CREATE INDEX IF NOT EXISTS idx_sessions_visitor ON sessions(visitor_id);
CREATE INDEX IF NOT EXISTS idx_sessions_customer ON sessions(customer_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);

CREATE INDEX IF NOT EXISTS idx_abandoned_carts_email ON abandoned_carts(email);
CREATE INDEX IF NOT EXISTS idx_abandoned_carts_recovered ON abandoned_carts(recovered);

CREATE INDEX IF NOT EXISTS idx_affiliate_events_affiliate ON affiliate_events(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_affiliate_events_type ON affiliate_events(event_type);

CREATE INDEX IF NOT EXISTS idx_marketplace_orders_marketplace ON marketplace_orders(marketplace);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Function to generate order number
CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TRIGGER AS $$
DECLARE
  prefix TEXT;
  year_part TEXT;
  sequence_num INTEGER;
  new_order_number TEXT;
BEGIN
  SELECT value::text INTO prefix FROM store_settings WHERE key = 'order_prefix';
  prefix := COALESCE(TRIM(BOTH '"' FROM prefix), 'LC');
  year_part := TO_CHAR(NOW(), 'YYYY');

  SELECT COALESCE(MAX(CAST(SUBSTRING(order_number FROM '\d+$') AS INTEGER)), 0) + 1
  INTO sequence_num
  FROM orders
  WHERE order_number LIKE prefix || '-' || year_part || '-%';

  new_order_number := prefix || '-' || year_part || '-' || LPAD(sequence_num::TEXT, 5, '0');
  NEW.order_number := new_order_number;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for order number generation
DROP TRIGGER IF EXISTS trigger_generate_order_number ON orders;
CREATE TRIGGER trigger_generate_order_number
  BEFORE INSERT ON orders
  FOR EACH ROW
  WHEN (NEW.order_number IS NULL)
  EXECUTE FUNCTION generate_order_number();

-- Function to update product rating
CREATE OR REPLACE FUNCTION update_product_rating()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE products
  SET
    rating = (SELECT ROUND(AVG(rating)::numeric, 1) FROM product_reviews WHERE product_id = NEW.product_id AND is_approved = true),
    reviews_count = (SELECT COUNT(*) FROM product_reviews WHERE product_id = NEW.product_id AND is_approved = true),
    updated_at = NOW()
  WHERE id = NEW.product_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for rating updates
DROP TRIGGER IF EXISTS trigger_update_rating ON product_reviews;
CREATE TRIGGER trigger_update_rating
  AFTER INSERT OR UPDATE ON product_reviews
  FOR EACH ROW
  EXECUTE FUNCTION update_product_rating();

-- Function to update customer stats
CREATE OR REPLACE FUNCTION update_customer_stats()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.payment_status = 'paid' THEN
    UPDATE customers
    SET
      total_orders = total_orders + 1,
      total_spent = total_spent + NEW.total,
      average_order_value = (total_spent + NEW.total) / (total_orders + 1),
      last_order_at = NOW(),
      first_order_at = COALESCE(first_order_at, NOW()),
      updated_at = NOW()
    WHERE id = NEW.customer_id;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for customer stats
DROP TRIGGER IF EXISTS trigger_update_customer_stats ON orders;
CREATE TRIGGER trigger_update_customer_stats
  AFTER INSERT OR UPDATE OF payment_status ON orders
  FOR EACH ROW
  WHEN (NEW.customer_id IS NOT NULL)
  EXECUTE FUNCTION update_customer_stats();

-- Function to log inventory changes
CREATE OR REPLACE FUNCTION log_inventory_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.stock_quantity != NEW.stock_quantity THEN
    INSERT INTO inventory_transactions (
      product_id,
      type,
      quantity_change,
      quantity_before,
      quantity_after,
      reference_type,
      notes
    ) VALUES (
      NEW.id,
      'adjustment',
      NEW.stock_quantity - OLD.stock_quantity,
      OLD.stock_quantity,
      NEW.stock_quantity,
      'manual',
      'Stock updated via admin'
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for inventory logging
DROP TRIGGER IF EXISTS trigger_log_inventory ON products;
CREATE TRIGGER trigger_log_inventory
  AFTER UPDATE OF stock_quantity ON products
  FOR EACH ROW
  EXECUTE FUNCTION log_inventory_change();

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on sensitive tables
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE affiliate_events ENABLE ROW LEVEL SECURITY;

-- Policy for admins (service role can access all)
CREATE POLICY "Service role has full access to admins" ON admins
  FOR ALL USING (true);

CREATE POLICY "Service role has full access to orders" ON orders
  FOR ALL USING (true);

CREATE POLICY "Service role has full access to customers" ON customers
  FOR ALL USING (true);

-- ============================================
-- SEED DATA - Default Admin
-- ============================================

-- Create default admin (password should be changed)
INSERT INTO admins (email, role, name)
VALUES ('admin@lumierecurves.shop', 'super_admin', 'Admin')
ON CONFLICT (email) DO NOTHING;

-- ============================================
-- VIEWS FOR ANALYTICS
-- ============================================

-- Daily Sales Summary View
CREATE OR REPLACE VIEW daily_sales_summary AS
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_orders,
  COUNT(*) FILTER (WHERE payment_status = 'paid') as paid_orders,
  SUM(total) FILTER (WHERE payment_status = 'paid') as revenue,
  AVG(total) FILTER (WHERE payment_status = 'paid') as avg_order_value,
  COUNT(DISTINCT customer_id) as unique_customers
FROM orders
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Product Performance View
CREATE OR REPLACE VIEW product_performance AS
SELECT
  p.id,
  p.name,
  p.sku,
  p.category,
  p.price,
  p.stock_quantity,
  COALESCE(SUM(oi.quantity), 0) as total_sold,
  COALESCE(SUM(oi.total_price), 0) as total_revenue,
  COUNT(DISTINCT oi.order_id) as order_count,
  p.rating,
  p.reviews_count
FROM products p
LEFT JOIN order_items oi ON p.id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.id AND o.payment_status = 'paid'
GROUP BY p.id, p.name, p.sku, p.category, p.price, p.stock_quantity, p.rating, p.reviews_count;

-- Customer Lifetime Value View
CREATE OR REPLACE VIEW customer_ltv AS
SELECT
  c.id,
  c.email,
  c.first_name,
  c.last_name,
  c.total_orders,
  c.total_spent,
  c.average_order_value,
  c.first_order_at,
  c.last_order_at,
  CASE
    WHEN c.last_order_at > NOW() - INTERVAL '30 days' THEN 'active'
    WHEN c.last_order_at > NOW() - INTERVAL '90 days' THEN 'at_risk'
    ELSE 'churned'
  END as status,
  DATE_PART('day', NOW() - c.last_order_at) as days_since_last_order
FROM customers c
WHERE c.total_orders > 0;

COMMIT;
