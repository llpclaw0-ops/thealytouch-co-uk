# Quote delivery configuration

The Aly Touch Contact page keeps visitors on-site through the four-step quote
flow. It is intentionally **not** connected to email yet: no business email
address or delivery service has been supplied, so the page correctly tells a
visitor that their request was not sent and offers the phone number instead.

When a business email address and a secure delivery service are ready, set the
`endpoint` value in `js/site.js` under `SITE.quoteDelivery`. The endpoint must
accept a JSON `POST` request and deliver it to the approved business inbox.
Do not put an email address in the public JavaScript or use `mailto:` as the
delivery mechanism. Test a real submission only after the recipient and
receiver have been approved.

The existing Mrs Jones questionnaire is separate and is not used, changed, or
redirected to by this Contact flow.
