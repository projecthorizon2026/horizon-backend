import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL || 'https://xarkrwgpyltlgtajnnfc.supabase.co',
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method === 'GET') {
    try {
      const { category, featured, active } = req.query;

      let query = supabase
        .from('products')
        .select('*')
        .order('created_at', { ascending: false });

      if (category) {
        query = query.eq('category', category);
      }

      if (featured === 'true') {
        query = query.eq('is_featured', true);
      }

      if (active !== 'false') {
        query = query.eq('is_active', true);
      }

      const { data, error } = await query;

      if (error) throw error;

      // Transform data to match frontend format
      const products = data.map(p => ({
        id: p.id,
        sku: p.sku,
        name: p.name,
        price: parseFloat(p.price),
        originalPrice: p.original_price ? parseFloat(p.original_price) : null,
        category: p.category,
        sizes: p.sizes || [],
        colors: p.colors || [],
        colorNames: p.colors?.map(c => c.name) || [],
        inStock: p.in_stock,
        stockQuantity: p.stock_quantity,
        stockNote: p.stock_quantity > 0 ? 'In Stock - Ships within 2 days' : 'Out of Stock',
        rating: parseFloat(p.rating) || 4.8,
        reviews: p.reviews_count || 0,
        badge: p.badge,
        image: p.images?.[0] || '',
        images: p.images || [],
        video: p.video,
        description: p.description,
        features: p.features || []
      }));

      res.status(200).json(products);
    } catch (error) {
      console.error('Error fetching products:', error);
      res.status(500).json({ error: error.message });
    }
  } else if (req.method === 'POST') {
    // Seed products endpoint
    try {
      const { products } = req.body;

      if (!products || !Array.isArray(products)) {
        return res.status(400).json({ error: 'Products array required' });
      }

      const dbProducts = products.map(p => ({
        sku: p.sku,
        name: p.name,
        slug: p.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        description: p.description,
        price: p.price,
        original_price: p.originalPrice,
        category: p.category,
        sizes: p.sizes,
        colors: p.colors?.map((hex, i) => ({ hex, name: p.colorNames?.[i] || 'Color' })) || [],
        in_stock: p.inStock !== false,
        stock_quantity: p.stockQuantity || 100,
        rating: p.rating || 4.8,
        reviews_count: p.reviews || 0,
        badge: p.badge,
        images: p.images || [p.image],
        video: p.video,
        features: p.features || [],
        is_active: true,
        is_featured: p.badge === 'Bestseller'
      }));

      // Upsert products (update if SKU exists, insert if not)
      const { data, error } = await supabase
        .from('products')
        .upsert(dbProducts, { onConflict: 'sku' })
        .select();

      if (error) throw error;

      res.status(200).json({ success: true, count: data.length, products: data });
    } catch (error) {
      console.error('Error seeding products:', error);
      res.status(500).json({ error: error.message });
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}
