# The database behind the demo

Querydesk currently runs for one standard customer analytics PostgreSQL database.

## Analytics data: customers and orders

The demo analytics database is named `nl2sql_demo` and uses PostgreSQL. It models a straightforward sales workflow: customers place orders, and each order can contain multiple product line items. 

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--o{ ORDER_ITEMS : contains

    CUSTOMERS {
        bigint customer_id PK
        varchar name
        varchar email UK
        varchar country
        varchar segment
        date signup_date
        boolean is_active
    }
    ORDERS {
        bigint order_id PK
        bigint customer_id FK
        timestamp order_date
        varchar status
        decimal total_amount
        decimal discount_amount
    }
    ORDER_ITEMS {
        bigint order_id PK, FK
        bigint product_id PK
        varchar product_name
        varchar category
        int quantity
        decimal unit_price
    }
```

`customers` has one row per customer. `orders` has one row per order and points to the customer who placed it. `order_items` has one row per product in an order; its primary key is the pair `(order_id, product_id)`. An order may have no items, and a customer may have no orders. To connect customers to products, join through `orders` rather than joining customers directly to `order_items`.

## Business meaning matters

The schema is deliberately small, but several business rules change what a correct answer means:

- Revenue is the sum of `orders.total_amount` for orders with status `CONFIRMED`, `SHIPPED`, or `DELIVERED`. Pending and cancelled orders are excluded.
- Product sales value is `quantity * unit_price` summed over eligible order items. It can differ from order totals because order discounts are not apportioned to products.
- For product units sold, sum `order_items.quantity` for items in eligible orders.
- Joining orders to items repeats each order once per item. Use `COUNT(DISTINCT orders.order_id)` for order counts after that join, and avoid summing order totals across duplicated rows.
- `orders.total_amount` is the canonical order total, in USD. It includes applicable discounts; tax and shipping are not separate columns.
- `customers.country` is the customer's registered country. There is no state or order-destination column, so a request specifically about a US state cannot be answered from this schema.
- Inactive customers can still have historical orders. Do not exclude them unless the question asks for active customers.

These definitions live in the root `SCHEMA.md`. The model uses them when writing SQL, and they help the system ask for clarification when a request cannot be represented by the available columns.

For a fuller explanation of retrieval and the safeguards before execution, see [Architecture and workflow](architecture.md).

## Chat and feedback storage

The second PostgreSQL database is `querydesk_app`. It is for the application, not for analytics. The API creates these tables on startup:

```mermaid
erDiagram
    CONVERSATION ||--o{ MESSAGES : contains
    MESSAGES ||--o| FEEDBACK : receives

    CONVERSATION {
        string id PK
        string user_id
        string title
        datetime created_at
        datetime updated_at
    }
    MESSAGES {
        string id PK
        string conversation_id FK
        string user_id
        string role
        text content
        json payload
        datetime created_at
    }
    FEEDBACK {
        string id PK
        string message_id FK
        string user_id
        string rating
        text comment
        datetime created_at
        datetime updated_at
    }
```

Each conversation belongs to a user. Messages are attached to a conversation and carry the same `user_id`; feedback belongs to an assistant message and its user.
