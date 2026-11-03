# Sources

Official documents used by the assistant. Update this file every time a
document is added, replaced, or re-downloaded. Original files in this
folder are never edited.

---

## 1. Summary of MSME related Loan Schemes

- **File:** data/raw/treasury_msme_loan_schemes_summary.pdf
- **Issuing body:** Government of Sri Lanka, Treasury / Ministry of Finance (Department of Development Finance)
- **Download URL:** https://www.treasury.gov.lk/api/file/02a6d40c-58ee-4a97-a203-5a9e56333fda  (CONFIRM this link produced this file)
- **Downloaded on:** 2026-10-14
- **Document date / version:** no date printed on the document; file metadata says created 2025-02-05 (made in Excel)
- **Pages:** 2
- **Type:** text PDF (text is selectable)
- **Tables:** yes, the whole document is one wide comparison table (pages 1-2)
- **Schemes covered:** SMELoC (ADB), SMELOC2 (ADB), Re-energizing the MSME Sector Component I (GoSL), Re-energizing Component II / NPL (GoSL)
- **Compares:** eligible categories and sectors, loan types, source of fund, eligibility criteria, and more
- **Notes:** Table layout will break naive text extraction. Test table parsing early. Best document for "compare scheme A vs B" questions.

---

## 2. Re-energizing the MSME Sector: Government Funded Loan Scheme Operating Guideline

- **File:** data/raw/re_msme_operating_guideline.pdf
- **Issuing body:** Department of Development Finance, Ministry of Finance, Economic Stabilization and National Policies
- **Reference no.:** DFD/2024/LF/OG/01
- **Download URL:** https://neda.gov.lk/wp-content/uploads/2024/06/OG-GoSL-Funded-Loan-Scheme-final.pdf  (CONFIRM this link produced this file)
- **Downloaded on:** 2026-10-14
- **Document date / version:** dated 02 May 2024 on the cover (file metadata: 2024-05-14)
- **Pages:** 21
- **Type:** text PDF (text is selectable)
- **Structure:** sections 1-9 on pages 2-13; Annex I (registration application) p14; sector/size criteria table p16; Annex II p17; Annex III (refinance application) p18; Annex IV p19; Annex V p20; Annex VI (working capital loan application, NPL) p21
- **Schemes covered:** Re-energizing the MSME Sector only (Component I: strengthening existing MSMEs and start-ups; Component II: MSMEs in NPL category)
- **Notes:** Says the interest rate will be revised by DFD according to market fluctuations, so rates in this document may be out of date. Best document for process, roles, and application steps.

---

## 3. Treasury MSME Loan Scheme FAQ (web page saved as PDF)

- **File:** data/raw/treasury_msme_faq.pdf
- **Issuing body:** Ministry of Finance, The Treasury of Sri Lanka
- **Download URL:** https://www.treasury.gov.lk/web/frequently-asked-questions/section/msme%20loans
- **Downloaded on:** 2026-10-14
- **Document date / version:** web page; the site footer shows "Last updated: 14 October 2026", which is likely the whole site and not this content. Use the download date.
- **Pages:** 12
- **Type:** text PDF (browser print of the page)
- **Tables:** yes, the answers to the questions on limits, criteria, grace periods and required documents are in tables
- **Schemes covered:** SMELoC, SMELOC2, Re-energizing MSME (Components I and II)
- **Contents:** 18 questions, including loan schemes, eligible sectors, maximum loan, repayment, grace period, collateral, participating banks, application process, required documents, business registration
- **Notes:** Includes site menus and header text that should be removed before indexing. Web pages change without notice, so the download date matters.

---

## Overlaps and conflicts to check (not yet verified)

- [ ] Do the Summary (2025), the Guideline (May 2024) and the FAQ (Oct 2026) agree on maximum loan amounts?
- [ ] Do they agree on interest-rate caps, grace periods and repayment terms?
- [ ] FAQ lists different participating banks in two columns, apparently per scheme. Confirm which column belongs to which scheme.
- [ ] Is anything in the Guideline (2024) superseded by the Summary (2025) or the FAQ?

## Documents still missing

- [ ] SMELoC and SMELOC2 operating guidelines (only the summary and FAQ cover them so far)
- [ ] Bank-specific application forms or requirements
- [ ] Gazette No. 2264/18 (mentioned in the FAQ for the environmental protection license)
