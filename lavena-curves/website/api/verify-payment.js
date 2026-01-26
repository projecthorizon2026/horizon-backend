import crypto from 'crypto';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL || 'https://xarkrwgpyltlgtajnnfc.supabase.co',
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Generate order number
async function generateOrderNumber() {
  const year = new Date().getFullYear();
  const prefix = 'LC';

  const { count } = await supabase
    .from('orders')
    .select('*', { count: 'exact', head: true })
    .like('order_number', `${prefix}-${year}-%`);

  const sequence = (count || 0) + 1;
  return `${prefix}-${year}-${String(sequence).padStart(5, '0')}`;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const {
      razorpay_order_id,
      razorpay_payment_id,
      razorpay_signature,
      // Order details from frontend
      orderDetails
    } = req.body;

    // Verify signature
    const sign = razorpay_order_id + '|' + razorpay_payment_id;
    const expectedSign = crypto
      .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET)
      .update(sign)
      .digest('hex');

    if (razorpay_signature !== expectedSign) {
      return res.status(400).json({ error: 'Invalid payment signature', success: false });
    }

    // Generate order number
    const orderNumber = await generateOrderNumber();

    // Create or find customer
    let customerId = null;
    if (orderDetails?.customer?.email) {
      const { data: existingCustomer } = await supabase
        .from('customers')
        .select('id')
        .eq('email', orderDetails.customer.email.toLowerCase())
        .single();

      if (existingCustomer) {
        customerId = existingCustomer.id;
      } else {
        const { data: newCustomer } = await supabase
          .from('customers')
          .insert({
            email: orderDetails.customer.email.toLowerCase(),
            phone: orderDetails.customer.phone,
            first_name: orderDetails.customer.firstName,
            last_name: orderDetails.customer.lastName,
            addresses: [orderDetails.shippingAddress]
          })
          .select()
          .single();

        if (newCustomer) {
          customerId = newCustomer.id;
        }
      }
    }

    // Create order
    const { data: order, error: orderError } = await supabase
      .from('orders')
      .insert({
        order_number: orderNumber,
        customer_id: customerId,
        status: 'confirmed',
        payment_status: 'paid',
        payment_method: 'razorpay',
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature,
        subtotal: orderDetails?.subtotal || 0,
        shipping_cost: orderDetails?.shippingCost || 0,
        total: orderDetails?.total || 0,
        shipping_address: orderDetails?.shippingAddress || {},
        customer_name: `${orderDetails?.customer?.firstName || ''} ${orderDetails?.customer?.lastName || ''}`.trim(),
        customer_email: orderDetails?.customer?.email,
        customer_phone: orderDetails?.customer?.phone,
        source: 'website'
      })
      .select()
      .single();

    if (orderError) {
      console.error('Order creation error:', orderError);
      // Even if order save fails, payment was successful
      return res.status(200).json({
        success: true,
        message: 'Payment verified (order save pending)',
        paymentId: razorpay_payment_id,
        orderId: razorpay_order_id,
        orderNumber: null
      });
    }

    // Create order items
    if (orderDetails?.items?.length > 0 && order) {
      const orderItems = orderDetails.items.map(item => ({
        order_id: order.id,
        product_id: item.productId || null,
        product_name: item.name,
        product_image: item.image,
        sku: item.sku,
        size: item.selectedSize,
        color: item.selectedColor,
        quantity: item.quantity,
        unit_price: item.price,
        total_price: item.price * item.quantity
      }));

      await supabase.from('order_items').insert(orderItems);
    }

    // Update customer stats
    if (customerId) {
      await supabase.rpc('update_customer_order_stats', {
        p_customer_id: customerId,
        p_order_total: orderDetails?.total || 0
      }).catch(() => {
        // Ignore if RPC doesn't exist
      });
    }

    res.status(200).json({
      success: true,
      message: 'Payment verified and order created',
      paymentId: razorpay_payment_id,
      orderId: razorpay_order_id,
      orderNumber: order?.order_number
    });

  } catch (error) {
    console.error('Error verifying payment:', error);
    res.status(500).json({ error: error.message || 'Payment verification failed', success: false });
  }
}
