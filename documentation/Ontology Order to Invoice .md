## **Example workflow**

1. A customer places an order by email, phone, WhatsApp, or form.  
2. Someone on the team manually checks the order details.  
3. The team verifies customer identity, pricing, stock, and payment terms.  
4. If stock exists, the order is approved and prepared.  
5. If stock is missing, the team checks alternatives or delays the order.  
6. The order is entered into the system or spreadsheet.  
7. The warehouse picks, packs, and ships the goods, or the service team prepares delivery.  
8. An invoice is created manually or semi-manually.  
9. Payment is tracked and followed up if overdue.  
10. The order is closed once payment and delivery are complete.

## **Actors involved**

* Customer.  
* Sales or customer service staff.  
* Operations manager.  
* Warehouse staff.  
* Accounting or finance staff.  
* Administrator.  
* Delivery partner or logistics provider.  
* Business owner, if approval is needed.

## **Pain points**

* Orders come from multiple channels and are easy to miss.  
* Data is entered more than once.  
* Stock information is often outdated.  
* Invoice creation is delayed.  
* Teams rely on spreadsheets and memory.  
* People spend time checking basic things that should be automatic.  
* No clear visibility into order status.  
* Exceptions are handled manually and inconsistently.

## **Exceptions and edge cases**

* Customer places an urgent order.  
* Item is out of stock.  
* Price differs from the standard price list.  
* Customer has special payment terms.  
* Order contains a mix of in-stock and backordered items.  
* Duplicate order is accidentally created.  
* Customer changes the order after confirmation.  
* Invoice must be corrected after shipping.  
* Partial payment is received.  
* The customer disputes the order or invoice.

## **Goal of the process**

The goal is to move an order from request to payment with minimal manual work, few errors, and full visibility across sales, inventory, and finance.

## **KPIs for success**

* Order processing time.  
* Percentage of orders entered without error.  
* Invoice creation delay.  
* Stock accuracy.  
* Number of manual touchpoints per order.  
* Percentage of orders fulfilled on time.  
* Percentage of invoices paid on time.  
* Number of exceptions handled manually.  
* Number of duplicate orders.  
* Customer response time.

## **Ontology Input Document**

## **1\) Scope**

Process: Order-to-Invoice.  
Purpose: model the business meaning, allowed actions, and key rules for handling customer orders, stock, shipping, invoicing, and payment.

## **2\) Business goal**

Move an order from request to payment with minimal manual work, fewer errors, and full visibility across sales, operations, inventory, and finance.

## **3\) Core entities**

* Customer.  
* Order.  
* OrderLine.  
* Product.  
* StockItem.  
* Warehouse.  
* Shipment.  
* Invoice.  
* InvoiceLine.  
* Payment.  
* User.  
* Role.  
* Approval.  
* Exception.  
* PriceList.

## **4\) Key relationships**

* Customer places Order.  
* Order contains OrderLines.  
* OrderLine refers to Product.  
* Product is linked to StockItem.  
* StockItem is stored in Warehouse.  
* Order triggers Shipment.  
* Shipment supports Invoice.  
* Invoice contains InvoiceLines.  
* Payment settles Invoice.  
* User has Role.  
* Role permits Action.  
* Action may require Approval.  
* Exception is raised when rule is violated.

## **5\) Allowed actions**

* Create Order.  
* Update Order.  
* Reserve Stock.  
* Confirm Order.  
* Create Shipment.  
* Create Invoice.  
* Register Payment.  
* Cancel Order.  
* Approve Exception.

## **6\) Forbidden actions**

* Create records without permission.  
* Confirm order with insufficient stock unless exception is approved.  
* Create invoice for an unapproved cancelled order.  
* Change price without role authorization.  
* Ship without valid order status.  
* Edit invoice after posting unless correction flow is used.

## **7\) Business rules**

* An order must have at least one order line.  
* Every order line must reference one product.  
* Only authorized roles may approve price changes.  
* Stock must be available before shipment unless backorder is allowed.  
* Invoice must match the approved order or approved exception.  
* Payment status must be linked to invoice status.  
* Every blocked action must create an exception record.

## **8\) Exceptions and edge cases**

* Out-of-stock order.  
* Partial shipment.  
* Partial payment.  
* Duplicate order.  
* Price override request.  
* Customer order change after confirmation.  
* Invoice correction after posting.  
* Urgent order requiring manual approval.

## **9\) Roles**

* Sales staff.  
* Customer service.  
* Warehouse staff.  
* Accounting staff.  
* Manager.  
* Administrator.

## **10\) Required outputs for the ontology**

* Business glossary.  
* Entity list.  
* Relationship map.  
* Permission matrix.  
* Rule list.  
* Exception list.  
* One test scenario for allowed action.  
* One test scenario for blocked action.

## **11\) Success criteria**

* The ontology can explain who can do what.  
* The ontology can block invalid actions.  
* The ontology can support AI decisions without improvisation.  
* The ontology can map to real ERP data and workflows.

