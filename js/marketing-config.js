/*
 * Marketing tag IDs for the public HomecareOS website only
 * (homecareos.co.uk). They are not used on the app or the carer app.
 *
 * Leave these empty until the IDs have been added. An empty value means
 * that tag never loads, even after advertising cookies are accepted.
 *
 * META_PIXEL_ID
 *   Meta Events Manager → Data Sources → create a Pixel / Dataset.
 *   Copy the Pixel ID (numbers only).
 *
 * LINKEDIN_PARTNER_ID
 *   LinkedIn Campaign Manager → Analyze → Insight Tag.
 *   Copy the Partner ID (numbers only).
 *
 * LINKEDIN_CONVERSION_ID
 *   LinkedIn Campaign Manager → Analyze → Conversion tracking.
 *   Create a website conversion for a Lead (demo booking, contact
 *   message, or Get started click) and copy its conversion ID.
 *   Page views still work from the Partner ID alone; Lead events wait
 *   for this value.
 *
 * After pasting the IDs, the change still needs a review and a merge
 * before it is live. Do not commit a real ID in a public comment.
 *
 * Server-side Conversions API (Meta CAPI and LinkedIn CAPI) is planned
 * so browser events can be sent with a matching event ID and survive
 * cookie restrictions. It is not built in this change.
 */
window.HCOS_MARKETING = {
  META_PIXEL_ID: '',
  LINKEDIN_PARTNER_ID: '',
  LINKEDIN_CONVERSION_ID: ''
};
