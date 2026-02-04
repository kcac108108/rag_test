Tables:
- orders(order_id PK, customer_id, order_date, status, total_amount)
- customers(customer_id PK, customer_name, country)

Relationships:
- orders.customer_id -> customers.customer_id
