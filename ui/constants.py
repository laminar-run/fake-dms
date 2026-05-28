"""Shared dropdown / option constants for DealerDesk 98."""

SALESPEOPLE = ["Jordan Miller", "Alex Chen", "Sam Rivera", "Pat Johnson", "Chris Lee"]
ADVISORS = ["Robin Davis", "Casey Brooks", "Morgan Hayes", "Taylor Quinn"]
STAFF = SALESPEOPLE + ADVISORS

CUSTOMER_TYPES = ["Retail", "Fleet", "Internal"]
STATES = ["IL", "CA", "TX", "SC", "WI", "KY", "TN", "OR", "VA", "AL",
          "NY", "FL", "OH", "GA", "NC", "MI", "PA", "AZ", "WA", "CO"]

MAKES = ["Ford", "Toyota", "Honda", "Chevrolet", "Nissan", "Jeep",
         "Subaru", "Ram", "GMC", "Hyundai", "Kia", "Mazda"]
VEHICLE_STATUSES = ["In Stock", "Sold", "Customer-Owned", "In Service", "On Hold", "Wholesale"]

RO_TYPES = ["Maintenance", "Repair", "Warranty", "Recall", "Diagnostic", "Multi-Point Inspection"]
RO_STATUSES = ["Open", "In Progress", "Awaiting Parts", "Completed", "Closed", "Invoiced"]

DEAL_TYPES = ["Finance", "Lease", "Cash"]
DEAL_STATUSES = ["Quote", "Pending", "Approved", "Sold", "Delivered", "Dead"]

APPT_DEPTS = ["Service", "Sales"]
APPT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show", "Rescheduled"]
SERVICE_REASONS = ["Oil Change", "Tire Rotation", "Brake Inspection", "Check Engine Light",
                   "30K Mile Service", "60K Mile Service", "State Inspection", "Recall Service",
                   "Battery Replacement", "A/C Service", "Alignment", "Multi-Point Inspection"]
SALES_REASONS = ["Test Drive", "Trade Appraisal", "Finance Application", "Vehicle Delivery", "Sales Follow-Up"]
