# Database Schema and Business Semantics

> Fill in the sections below for this database. Keep database identifiers exactly as they appear in the database. Remove examples and placeholder comments once replaced. A context builder should be able to extract the database settings, table/column metadata, relationships, definitions, and caveats from this document.

## Database

* **Dialect:** PostgreSQL
* **Database/schema name:** `nl2sql_demo`
* **Default reporting timezone:** UTC. Date/time filters on `TIMESTAMP` columns should be interpreted in UTC.
* **Currency policy:** All monetary amounts are denominated in USD. Monetary amounts can be safely summed across rows within this database.

## Tables

### `customers`

* **Purpose:** Customers who can place orders.
* **Row grain:** One row per customer.
* **Primary key:** `customer_id`

| Column        | Type         | Nullable | Key / reference | Meaning                                                                                      |
| ------------- | ------------ | -------- | --------------- | -------------------------------------------------------------------------------------------- |
| `customer_id` | BIGINT       | No       | PK              | Unique customer identifier.                                                                  |
| `name`        | VARCHAR(100) | No       |                 | Customer display name.                                                                       |
| `email`       | VARCHAR(255) | No       | UNIQUE          | Customer email address.                                                                      |
| `country`     | VARCHAR(50)  | No       |                 | Customer's registered country; not necessarily an order destination.                         |
| `segment`     | VARCHAR(20)  | No       |                 | Customer business segment. Values: `SMB`, `MID_MARKET`, `ENTERPRISE`.                        |
| `signup_date` | DATE         | No       |                 | Registration date, not first-order date.                                                     |
| `is_active`   | BOOLEAN      | No       |                 | Whether the account is currently active; historical orders may belong to inactive customers. |

### `orders`

* **Purpose:** Orders placed by customers.
* **Row grain:** One row per order.
* **Primary key:** `order_id`

| Column            | Type          | Nullable | Key / reference              | Meaning                                                                                                                    |
| ----------------- | ------------- | -------: | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `order_id`        | BIGINT        |       No | PK                           | Unique order identifier.                                                                                                   |
| `customer_id`     | BIGINT        |       No | FK → `customers.customer_id` | Customer who placed the order.                                                                                             |
| `order_date`      | TIMESTAMP     |       No |                              | Time the order was placed; not delivery or payment time.                                                                   |
| `status`          | VARCHAR(20)   |       No |                              | Lifecycle status: `PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`.                                             |
| `total_amount`    | DECIMAL(12,2) |       No |                              | Final order amount in USD, including applicable discounts. Tax and shipping are not separately represented in this schema. |
| `discount_amount` | DECIMAL(12,2) |       No | Default 0                    | Total discount applied to the order, in USD.                                                                               |

### `order_items`

* **Purpose:** Products recorded within orders.
* **Row grain:** One row per product within an order.
* **Primary key:** (`order_id`, `product_id`)

| Column         | Type          | Nullable | Key / reference                      | Meaning                                                                                                            |
| -------------- | ------------- | -------: | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `order_id`     | BIGINT        |       No | PK component; FK → `orders.order_id` | Order containing the product.                                                                                      |
| `product_id`   | BIGINT        |       No | PK component                         | Product identifier; no product master table exists in this schema.                                                 |
| `product_name` | VARCHAR(150)  |       No |                                      | Product name at time of purchase.                                                                                  |
| `category`     | VARCHAR(100)  |       No |                                      | Product category at time of purchase.                                                                              |
| `quantity`     | INT           |       No |                                      | Units purchased.                                                                                                   |
| `unit_price`   | DECIMAL(12,2) |       No |                                      | Price per unit for this order item in USD. This is the price charged for the item before any order-level discount. |

## Relationships

| From        | To            | Join condition                               | Cardinality / notes                                               |
| ----------- | ------------- | -------------------------------------------- | ----------------------------------------------------------------- |
| `customers` | `orders`      | `customers.customer_id = orders.customer_id` | One customer to zero or more orders; each order has one customer. |
| `orders`    | `order_items` | `orders.order_id = order_items.order_id`     | One order to zero or more items.                                  |
| `customers` | `order_items` | Via `orders`                                 | No direct relationship; join through `orders`.                    |

## Business definitions

| Term                         | Definition / formula                                            | Required filters and caveats                                                                                                                                                                          |
| ---------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Revenue                      | Sum of `orders.total_amount`.                                   | Revenue includes only orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`. `PENDING` and `CANCELLED` orders do not count as revenue.                                                        |
| Order value                  | `orders.total_amount`.                                          | Do not assume it equals the sum of item values.                                                                                                                                                       |
| Product/category sales value | `SUM(order_items.quantity * order_items.unit_price)`.           | Include only items belonging to orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`. May not reconcile to order totals because order-level discounts are not allocated to individual items. |
| Units sold                   | `SUM(order_items.quantity)`.                                    | Include only items belonging to orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`.                                                                                                        |
| Order count                  | `COUNT(DISTINCT orders.order_id)` when joined to `order_items`. | Order count includes all statuses unless the question explicitly specifies a status filter. A join to items duplicates order rows.                                                                    |
| Customer spend               | Sum of non-cancelled `orders.total_amount` per customer.        | Use only orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`. Avoid summing order totals after joining to items unless totals are deduplicated first.                                       |

## Global data rules and caveats

* Inactive customers may have historical orders; do not exclude them unless requested.
* **Revenue, product/category sales value, units sold, and customer spend include only orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`.**
* Pending and cancelled orders are excluded from revenue and sales metrics.
* Cancelled and pending orders remain relevant to historical order-count questions unless a status filter is explicitly requested.
* Joining `orders` to `order_items` creates multiple rows per order; order-level measures can be duplicated.
* There are no test/demo orders, soft-delete columns, tenant boundaries, or archived-record filters in this schema.
* All monetary values are in USD.
* `product_id` has no foreign-key relationship to a separate product master table.
* `product_name` and `category` describe the product as recorded at the time of purchase and may not represent current product metadata.
* `orders.total_amount` is the canonical order-level monetary value for revenue and customer-spend calculations.
* `order_items.quantity * order_items.unit_price` is the canonical item-level sales value for product and category analysis; it should not be assumed to reconcile exactly with `orders.total_amount`.

## Optional question-to-schema examples

| Natural-language question                                                         | Expected tables                      | Metric / filters / grouping                                                                                                                                                                                                                                            |
| --------------------------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| How many active customers are there in each country?                              | `customers`                          | Count customers where `is_active = TRUE`, grouped by `country`.                                                                                                                                                                                                        |
| What are the top 10 customers by revenue?                                         | `customers`, `orders`                | Sum `orders.total_amount` for orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`, grouped by customer, ordered descending, limit 10.                                                                                                                        |
| What are the top 5 products by units sold?                                        | `order_items`, `orders`              | Sum `order_items.quantity` for orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`, grouped by `product_id` and `product_name`, ordered descending, limit 5.                                                                                                 |
| Which product category generated the most sales?                                  | `orders`, `order_items`              | Sum `quantity * unit_price` for orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`, grouped by `category`, ordered descending.                                                                                                                              |
| Which customers have never placed an order?                                       | `customers`, `orders`                | LEFT JOIN customers to orders and select customers with no matching order.                                                                                                                                                                                             |
| Which customers have purchased products from at least three different categories? | `customers`, `orders`, `order_items` | Count distinct `category` per customer for orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')` and filter for `COUNT(DISTINCT category) >= 3`.                                                                                                               |
| Show monthly revenue for the last 12 months.                                      | `orders`                             | Use the 12 calendar months ending with the current calendar month based on the query run date, interpreted in UTC. Include only orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')`, group by calendar month, sum `total_amount`, and order chronologically. |
| Which customers have spent more than the average customer spend?                  | `customers`, `orders`                | Calculate spend using orders with `status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')` per customer, then compare each customer's spend against the average customer spend.                                                                                               |
