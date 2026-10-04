-- Idempotent demo dataset: 12 customers, 15 orders, and 15 order items.
INSERT INTO customers (customer_id, name, email, country, segment, signup_date, is_active) VALUES
(1, 'Asha Patel', 'asha@example.com', 'India', 'SMB', '2024-01-15', TRUE),
(2, 'Noah Williams', 'noah@example.com', 'USA', 'ENTERPRISE', '2023-09-02', TRUE),
(3, 'Mina Chen', 'mina@example.com', 'Singapore', 'MID_MARKET', '2024-05-21', FALSE),
(4, 'Liam Murphy', 'liam@example.com', 'UK', 'SMB', '2024-03-12', TRUE),
(5, 'Sofia Alvarez', 'sofia@example.com', 'Mexico', 'MID_MARKET', '2024-04-08', TRUE),
(6, 'Ethan Kim', 'ethan@example.com', 'South Korea', 'ENTERPRISE', '2023-12-19', TRUE),
(7, 'Priya Nair', 'priya@example.com', 'India', 'MID_MARKET', '2024-06-02', TRUE),
(8, 'Oliver Smith', 'oliver@example.com', 'UK', 'SMB', '2023-11-27', FALSE),
(9, 'Fatima Hassan', 'fatima@example.com', 'UAE', 'ENTERPRISE', '2024-02-14', TRUE),
(10, 'Lucas Silva', 'lucas@example.com', 'Brazil', 'SMB', '2024-07-09', TRUE),
(11, 'Emma Johnson', 'emma@example.com', 'USA', 'MID_MARKET', '2024-08-17', TRUE),
(12, 'Arjun Mehta', 'arjun@example.com', 'India', 'ENTERPRISE', '2023-10-05', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO orders (order_id, customer_id, order_date, status, total_amount, discount_amount) VALUES
(1001, 1, (CURRENT_DATE - INTERVAL '9 months')::timestamp, 'DELIVERED', 240.00, 10.00),
(1002, 1, (CURRENT_DATE - INTERVAL '7 months')::timestamp, 'PENDING', 75.00, 0.00),
(1003, 2, (CURRENT_DATE - INTERVAL '2 months')::timestamp, 'SHIPPED', 520.00, 20.00),
(1004, 3, (CURRENT_DATE - INTERVAL '1 month')::timestamp, 'CANCELLED', 120.00, 0.00),
(1005, 1, (CURRENT_DATE - INTERVAL '8 months')::timestamp, 'DELIVERED', 220.00, 30.00),
(1006, 2, (CURRENT_DATE - INTERVAL '6 months')::timestamp, 'SHIPPED', 800.00, 0.00),
(1007, 3, (CURRENT_DATE - INTERVAL '5 months')::timestamp, 'PENDING', 35.00, 0.00),
(1008, 4, (CURRENT_DATE - INTERVAL '4 months')::timestamp, 'CONFIRMED', 48.00, 2.00),
(1009, 5, (CURRENT_DATE - INTERVAL '3 months')::timestamp, 'DELIVERED', 60.00, 0.00),
(1010, 6, (CURRENT_DATE - INTERVAL '2 months')::timestamp, 'CANCELLED', 150.00, 0.00),
(1011, 7, (CURRENT_DATE - INTERVAL '1 month')::timestamp, 'DELIVERED', 210.00, 0.00),
(1012, 8, (CURRENT_DATE - INTERVAL '20 days')::timestamp, 'CONFIRMED', 36.00, 0.00),
(1013, 9, (CURRENT_DATE - INTERVAL '12 days')::timestamp, 'SHIPPED', 80.00, 0.00),
(1014, 10, (CURRENT_DATE - INTERVAL '6 days')::timestamp, 'CANCELLED', 400.00, 0.00),
(1015, 11, (CURRENT_DATE - INTERVAL '2 days')::timestamp, 'DELIVERED', 100.00, 0.00)
ON CONFLICT DO NOTHING;

INSERT INTO order_items (order_id, product_id, product_name, category, quantity, unit_price) VALUES
(1001, 501, 'Desk Lamp', 'Home', 2, 100.00),
(1001, 502, 'Notebook Set', 'Office', 2, 25.00),
(1002, 501, 'Desk Lamp', 'Home', 1, 75.00),
(1003, 503, 'Monitor', 'Electronics', 1, 520.00),
(1004, 504, 'Water Bottle', 'Outdoors', 2, 60.00),
(1005, 505, 'Wireless Earbuds', 'Electronics', 1, 150.00),
(1005, 506, 'Mechanical Keyboard', 'Electronics', 1, 100.00),
(1006, 507, 'Monitor Stand', 'Office', 2, 400.00),
(1007, 508, 'Ceramic Mug', 'Home', 1, 35.00),
(1008, 509, 'Coffee Beans', 'Grocery', 2, 25.00),
(1009, 510, 'Yoga Mat', 'Sports', 2, 30.00),
(1010, 511, 'Travel Backpack', 'Outdoors', 1, 150.00),
(1011, 512, 'Desk Lamp', 'Home', 2, 105.00),
(1012, 513, 'Notebook Set', 'Office', 3, 12.00),
(1013, 514, 'Water Bottle', 'Outdoors', 2, 40.00)
ON CONFLICT DO NOTHING;
