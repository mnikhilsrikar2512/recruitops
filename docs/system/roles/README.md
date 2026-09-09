# Role Lifecycle Guides

This folder contains dedicated lifecycle guides for each universal role in the recruitment platform.

These files should be used when designing:

- navigation and dashboards
- backend permissions
- workflow ownership
- record visibility
- API access rules
- future role-specific frontend pages

## Source Of Truth

These guides are based on:

- `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md`
- `docs/system/ROLE_LIFECYCLE_AND_SYSTEM_FLOW.md`
- `docs/system/MODULES_AND_FEATURES.md`

## Role Files

- [Platform Admin Lifecycle](PLATFORM_ADMIN_LIFECYCLE.md)
- [Operations Admin Lifecycle](OPERATIONS_ADMIN_LIFECYCLE.md)
- [Business Lead Lifecycle](BUSINESS_LEAD_LIFECYCLE.md)
- [Client Manager Lifecycle](CLIENT_MANAGER_LIFECYCLE.md)
- [Delivery Lead Lifecycle](DELIVERY_LEAD_LIFECYCLE.md)
- [Recruiter Lifecycle](RECRUITER_LIFECYCLE.md)
- [Sourcing Support Lifecycle](SOURCING_SUPPORT_LIFECYCLE.md)
- [Reviewer Lifecycle](REVIEWER_LIFECYCLE.md)
- [External User Lifecycle](EXTERNAL_USER_LIFECYCLE.md)

## Access Mapping

- [Role Access Matrix](ROLE_ACCESS_MATRIX.md)

## Usage Rule

These are product capability guides, not customer-specific job titles.

Examples:

- one customer may map `Director` to `business_lead`
- another may map `Director` to `platform_admin`
- one customer may map `Lead Recruiter` to `delivery_lead`
- another may map `Delivery Manager` to `delivery_lead`

Always keep business titles configurable and product permissions stable.
