# Eval questions (draft v1)

Drafted from the 3 PDFs in data/raw/. Page numbers are PDF page numbers
(page 1 = first page of the file).

HOW TO USE THIS FILE
- Verify EVERY expected answer yourself against the page cited before you
  trust it. These are a draft, and any mistake here becomes a wrong "correct" answer.
- Fix or delete anything that does not match the document.
- Later, each question is run through the app and scored:
  1. Retrieval: was the cited page in the retrieved chunks?
  2. Correctness: does the answer match "Expected"?
  3. Citation: does it cite the right file + page?
  4. Refusal: for IDK questions, does it say it doesn't know instead of guessing?

Abbreviations: SUM = treasury_msme_loan_schemes_summary.pdf
               GL  = re_msme_operating_guideline.pdf
               FAQ = treasury_msme_faq.pdf
               Comp I / Comp II = Re-energizing the MSME Sector, Component I / II

IMPORTANT FINDING: GL p13, section 10, says the Re-energizing scheme runs
from 02 May 2024 and "shall be terminated on May 01, 2026". The FAQ (saved
14 Oct 2026) still lists it. Nothing in your 3 files says it was extended.
The app must handle this honestly (see Q28).

---

## A. Eligibility

Q01 | easy
Q: Does my business have to be registered to get a government SME loan?
Expected: Generally yes. Not-yet-registered businesses can submit evidence that their registration application was accepted by the Registrar of Companies / local government authority.
Source: SUM p1 (row 5); GL p3 (6.2.2); FAQ p1 (Q2), p11-12 (Q17)

Q02 | easy
Q: What are the turnover and employee limits to qualify?
Expected: Annual turnover below Rs. 1,000 million AND fewer than 200 employees (both conditions). For a group, the whole group's turnover counts.
Source: GL p3 (6.2.1); SUM p1 (row 5); FAQ p1 (Q2)

Q03 | medium
Q: Can I get a loan for a trading business or a shop that rents out equipment?
Expected: No. Trading, leasing and renting businesses are not eligible. Trading = buying finished products/services and reselling without value addition.
Source: GL p4 (6.3.3-6.3.4); FAQ p3 (Q5), p11 (Q16); SUM p1 (row 2)

Q04 | medium
Q: I became a non-performing borrower after the economic crisis. Can I still get a government loan?
Expected: Yes, possibly under Component II (NPL category), if the business is still operating and the default was due to unsettled loans from the recent downturn. Fully closed-down businesses are excluded. Willful defaulters and defaults due to fund diversion or fraud are not considered. Priority goes to those who became NPL as a guarantor for others' loans.
Source: GL p8 (7.2.1), p9 (7.2.2-7.2.3); SUM p1 (row 5)

Q05 | medium
Q: Do I have to be a Sri Lankan citizen?
Expected: The Re-energizing guideline (Comp I, and Comp II which adopts its criteria) lists "Be a citizen in Sri Lanka" as a requirement. The documents do not say this for SMELoC / SMELOC2.
Source: GL p4 (6.2.5), p8 (7.2)
Note: partly answerable. Good test of whether the app avoids over-generalising.

Q06 | medium
Q: What counts as a women-led enterprise?
Expected: At least 51% of ownership controlled by women; OR all three: at least 20% ownership by women, a woman is CEO or COO, and at least 30% of board members are women (where a board exists).
Source: GL p4 (6.3.2)

---

## B. Loan limits and terms

Q07 | easy
Q: What is the maximum loan amount under each scheme?
Expected: SMELoC Rs. 50M (multiple loans allowed up to 50M total); SMELOC2 Rs. 10M (one loan); Comp I Rs. 15M (one loan); Comp II Rs. 5M (one loan).
Source: SUM p1 (row 7); FAQ p4 (Q7); GL p3 (6.1.2), p8 (7.1.2)

Q08 | easy
Q: What is the maximum interest rate for each scheme?
Expected: SMELoC max 10% (current); SMELOC2 max 8%; Comp I max 7%; Comp II max 8%. Guideline notes rates may be revised by DFD with market rates.
Source: SUM p2 (row 8); FAQ p6 (Q11); GL p3 (6.1.9 + footnote 1), p8 (7.1.8)

Q09 | medium
Q: Is the interest rate fixed or can it change after I get the loan?
Expected: Under Comp I, the rate initially imposed on each borrower stays valid for the whole repayment period (DFD can revise the applicable rate for new loans). Banks may raise the rate to market rate under Comp II if the loan isn't settled within the original tenure, or if funds are misused.
Source: GL p3 (footnotes 1-2), p9 (7.2.4-7.2.5)

Q10 | easy
Q: What are the repayment and grace periods for each scheme?
Expected: SMELoC: up to 5 years incl. up to 2 years grace. SMELOC2: up to 3 years incl. 6 months grace. Comp I: up to 10 years incl. 12 months grace. Comp II: up to 5 years incl. 6 months grace. The bank decides the grace period actually approved.
Source: SUM p2 (rows 9-10); FAQ p5 (Q9-Q10); GL p3 (6.1.10-6.1.11), p8 (7.1.9-7.1.10)

Q11 | medium
Q: Which loan types are available (investment, working capital)?
Expected: SMELoC: investment, working capital, or combined. SMELOC2: working capital. Comp I: investment only. Comp II: working capital only.
Source: SUM p1 (row 3); FAQ p3 (Q6); GL p3 (6.1.3), p8 (7.1.3)

Q12 | medium
Q: How much of the project cost do I have to pay myself?
Expected: Comp I: minimum 10% equity contribution (cash or assets); bank loan up to 90% of estimated cost. Comp II: bank loan up to 100% of estimated cost (working capital).
Source: GL p3 (6.1.4-6.1.5), p8 (7.1.4)

Q13 | medium
Q: Do I need collateral?
Expected: Varies. SMELoC: working capital loans should be non-collateralised; for other loans the bank takes suitable collateral. SMELOC2 and Comp I: collateral as determined by the bank. Comp II: bank re-evaluates already-collateralised assets and may take new collateral if insufficient.
Source: SUM p2 (row 11); FAQ p6 (Q12); GL p4 (6.2.8), p10 (7.7)

---

## C. What it can be used for

Q14 | medium
Q: Can I use the loan to buy a vehicle?
Expected: Under Comp I, vehicle purchase is not allowed unless it is a land vehicle or the borrower is in the hotel or tourism sector.
Source: GL p4 (6.4b)

Q15 | medium
Q: Can I use the loan to pay off my existing loans?
Expected: Under Comp I, no. Loan proceeds cannot be used to settle existing loans.
Source: GL p4 (6.2.4)

---

## D. Documents

Q16 | medium
Q: What documents do I need to apply?
Expected: Descriptive project/business proposal; business registration copy (or the registration application copy / payment receipt if not yet registered); export proof if exporter; BOQ if construction; quotation if machinery purchase; Environment Protection License if a prescribed project (Gazette 2264/18, 27.01.2022). Comp II also: working capital computation. Comp I/II: Ministry of Industries recommendation letter. Annex II also lists CRIB report if not previously borrowed from a licensed bank.
Source: FAQ p11 (Q15); GL p17 (Annex II)

Q17 | hard
Q: What registration documents are needed for a sole proprietorship vs a private limited company?
Expected: Sole proprietorship/partnership: certificate of registration from the relevant local authority. Private limited company: Form 01 and other forms with directors, shareholders, company address. If no BR yet: payment receipt for applying for BR.
Source: GL p17 (Annex II item 1)

Q18 | hard
Q: I am an NPL applicant. What extra document do I need?
Expected: A working capital calculation as per the Annex V specimen (original), applicable only to Component II.
Source: GL p17 (Annex II item 3); FAQ p11 (specific criteria)

---

## E. Process and timelines

Q19 | medium
Q: How do I apply, step by step?
Expected: Comp I: get a Ministry of Industries recommendation letter via NEDA / IDB / Vidatha / SED officers (or MOI directly), then apply at a participating bank branch; branch manager approves and sends to head office; DFD approves and issues a No Objection Letter; bank disburses; bank applies to DFD for refinance. Comp II: MOI calls applications; apply to MOI officers; expert panel evaluates and issues a recommendation letter; apply at the same bank where you became NPL. SMELoC/SMELOC2: go directly to a participating bank branch.
Source: FAQ p7-10 (Q14); GL p5-6 (6.5-6.6), p9 (7.5)
Note: check FAQ p7 yourself to confirm which column is which scheme.

Q20 | medium
Q: How long does the Ministry of Industries take to issue the recommendation letter?
Expected: Within 5 working days of submitting the application. If delayed, the bank may tell the borrower to apply at the branch and process it without the MOI recommendation.
Source: GL p5 (6.5.3, 6.5.5)

Q21 | medium
Q: After the bank gets the No Objection Letter, how fast must the loan be disbursed?
Expected: Within 60 days of receiving the No Objection Letter, otherwise the sub-loan is automatically cancelled by the system.
Source: GL p6 (6.6.2)

Q22 | easy
Q: Can I apply through a finance company?
Expected: No. Only licensed banks implement the government-funded loan schemes.
Source: FAQ p12 (Q18)

---

## F. Comparison

Q23 | medium
Q: What's the difference between SMELoC and SMELOC2?
Expected: SMELoC: all sectors except trading/leasing/renting, up to Rs. 50M, investment/working capital/combined, max 10%, 5 years incl. 2 yrs grace. SMELOC2: MSMEs in agriculture, tourism, manufacturing, technology, export-oriented, and women-led, up to Rs. 10M, working capital only, max 8%, 3 years incl. 6 months grace. Both ADB-funded.
Source: SUM p1-2 (rows 2-10); FAQ p2-6

Q24 | hard
Q: I'm in tourism. Which schemes could I be eligible for?
Expected: SMELoC (all sectors except trading/leasing/renting), SMELOC2 (tourism listed), and Comp I (tourism listed in 6.3.1). Comp II only if NPL. Don't claim a single "best" scheme. Show options and limits.
Source: SUM p1 (row 2); GL p4 (6.3.1)

Q25 | hard
Q: Which scheme is cheapest in interest?
Expected: Comp I has the lowest maximum rate (7%), then SMELOC2 and Comp II (8%), then SMELoC (10%). These are maximum caps, not what a given bank will charge.
Source: SUM p2 (row 8)

---

## G. Scenarios (the example from the project note)

Q26 | hard
Q: I run a small garment factory with 30 employees and Rs. 40 million annual turnover. Can I get a government SME loan, and what documents do I need?
Expected: Meets the general limits (below Rs. 1,000M and 200 employees); apparel/manufacturing sectors are eligible under Comp I, SMELOC2 (manufacturing) and SMELoC. Options: Comp I up to Rs. 15M investment loan (max 7%), SMELOC2 up to Rs. 10M working capital, SMELoC up to Rs. 50M. Needs business registration, project proposal, bank evaluation, quotation if buying machinery, etc. Must state the scheme-validity caveat from Q28 and tell the user to confirm with a bank.
Source: GL p3-4, p17; SUM p1-2; FAQ p11
Must NOT: promise approval; give one fixed loan amount.

Q27 | hard
Q: My startup hasn't completed registration yet. Can I still apply for a loan?
Expected: Yes, you can submit evidence (a copy of the application / payment receipt) that your registration application has been accepted. Registration is compulsory for businesses already operating. Societies can borrow only for their own business activities, not to relend to members.
Source: SUM p1 (row 5); GL p3 (6.2.2), p17 (Annex II 1c); FAQ p11-12 (Q17)

---

## H. Should say "I don't know" or hedge

Q28 | hard (time-sensitive)
Q: Is the Re-energizing MSME loan scheme still open for applications today?
Expected: The guideline says the scheme runs from 2 May 2024 to 1 May 2026. The documents provided do not say whether it was extended. The app should say so and tell the user to confirm with the Department of Development Finance or a participating bank. It must not say "yes, it's open".
Source: GL p13 (section 10)

Q29 | medium
Q: What interest rate will Bank of Ceylon charge me?
Expected: I don't know. Documents give only the maximum rates for each scheme; the actual rate is set by the bank within the cap.
Must NOT: state a specific rate for a specific bank.

Q30 | medium
Q: If I meet all the criteria, will my loan definitely be approved?
Expected: No guarantee. The bank does its own credit assessment and due diligence, and DFD must register and approve the loan (No Objection Letter). Documents don't say what the bank's decision criteria will be.
Source: GL p6 (6.5.7-6.5.10)

Q31 | medium
Q: What is the minimum credit score or CRIB score I need?
Expected: I don't know. Documents mention a CRIB report for businesses that haven't borrowed from a licensed bank before, but give no minimum score.
Source: GL p17 (Annex II item 7)

Q32 | easy
Q: Can I get a loan under the "Rural Women Entrepreneur Loan Scheme"?
Expected: I don't know. That scheme is not in the provided documents. Don't invent details.

Q33 | easy
Q: What is the current Central Bank policy interest rate?
Expected: Out of scope. The assistant only covers government MSME loan documents.

---

## Notes for me
- Mix in more questions after reading the missing SMELoC and SMELOC2 guidelines.
- Add questions where two documents disagree, once found (see sources.md).
- Add a few typo-filled or informal questions ("loan for garment shop pls").
