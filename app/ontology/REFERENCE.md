# Mumbai Civic Ontology: reference

Version 0.2.0. Generated from the Turtle files in this folder by `hishob ontology build`; do not edit by hand. Marathi labels are drafts awaiting the language reviewer.

## Evidence

| Node label | English | Marathi | Properties |
|---|---|---|---|
| `Gap` | Gap | माहितीतील उणीव | `holder`, `name`, `name_en`, `name_mr`, `record_needed` |
| `SourceDocument` | Source document | स्रोत दस्तऐवज | `name`, `name_en`, `name_mr`, `publisher`, `sha256`, `title` |

## Money

| Node label | English | Marathi | Properties |
|---|---|---|---|
| `Allocation` | Allocation | तरतूद | `amount_actual`, `amount_be`, `amount_re`, `name`, `name_en`, `name_mr` |
| `BudgetHead` | Budget head | अर्थसंकल्पीय शीर्ष | `code`, `kind`, `name`, `name_en`, `name_mr` |
| `Expenditure` | Expenditure | खर्च | `amount`, `name`, `name_en`, `name_mr` |
| `FiscalYear` | Fiscal year | आर्थिक वर्ष | `name`, `name_en`, `name_mr`, `year_label` |
| `Payment` | Payment | देयक | `amount`, `name`, `name_en`, `name_mr`, `paid_on` |

## Org

| Node label | English | Marathi | Properties |
|---|---|---|---|
| `Agency` | Agency | प्राधिकरण | `name`, `name_en`, `name_mr` |
| `Department` | Department | खाते | `name`, `name_en`, `name_mr` |
| `IssueType` | Issue type | तक्रारीचा प्रकार | `code`, `name`, `name_en`, `name_mr` |
| `Person` | Person (public role only) | व्यक्ती (केवळ सार्वजनिक पद) | `name`, `name_en`, `name_mr` |
| `Post` | Post | पद | `name`, `name_en`, `name_mr`, `title` |
| `ServiceStandard` | Service standard | सेवा मानक | `days`, `name`, `name_en`, `name_mr` |

## Place

| Node label | English | Marathi | Properties |
|---|---|---|---|
| `AdminWard` | Administrative ward | प्रशासकीय विभाग (वॉर्ड) | `code`, `geometry_wkt`, `name`, `name_en`, `name_mr` |
| `Alias` | Alias | पर्यायी नाव | `name`, `name_en`, `name_mr` |
| `ElectoralWard` | Electoral ward | निवडणूक प्रभाग | `geometry_wkt`, `name`, `name_en`, `name_mr`, `number` |
| `Locality` | Locality | परिसर | `geometry_wkt`, `name`, `name_en`, `name_mr` |

## Procurement

| Node label | English | Marathi | Properties |
|---|---|---|---|
| `Award` | Award | कंत्राट वाटप | `awarded_on`, `name`, `name_en`, `name_mr`, `value` |
| `Bid` | Bid | बोली | `name`, `name_en`, `name_mr`, `value` |
| `Blacklisting` | Blacklisting | काळ्या यादीत समावेश | `from_date`, `name`, `name_en`, `name_mr`, `reason`, `to_date` |
| `Company` | Company | कंपनी | `name`, `name_en`, `name_mr`, `reg_no` |
| `Contract` | Contract | करार | `due_on`, `duration_days`, `name`, `name_en`, `name_mr`, `signed_on`, `value` |
| `Contractor` | Contractor | कंत्राटदार | `name`, `name_en`, `name_mr`, `reg_no` |
| `Corrigendum` | Corrigendum | शुद्धिपत्रक | `changed_field`, `name`, `name_en`, `name_mr`, `published_on`, `ref_no` |
| `Director` | Director | संचालक | `name`, `name_en`, `name_mr` |
| `Penalty` | Penalty | दंड | `amount`, `imposed_on`, `name`, `name_en`, `name_mr`, `reason` |
| `Tender` | Tender | निविदा | `bmc_bid_no`, `category`, `closes_on`, `emd`, `estimated_cost`, `name`, `name_en`, `name_mr`, `opened_on`, `published_on`, `ref_no`, `status`, `tender_id`, `title` |

## Works

| Node label | English | Marathi | Properties |
|---|---|---|---|
| `Asset` | Asset | मालमत्ता | `geometry_wkt`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `Bridge` | Bridge | पूल | `geometry_wkt`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `Building` | Building | इमारत | `geometry_wkt`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `DefectLiabilityPeriod` | Defect liability period | दोष दायित्व कालावधी | `from_date`, `name`, `name_en`, `name_mr`, `to_date` |
| `Drain` | Drain | नाला | `geometry_wkt`, `length_km`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `Garden` | Garden | उद्यान | `geometry_wkt`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `Hospital` | Hospital | रुग्णालय | `geometry_wkt`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `Inspection` | Inspection | तपासणी | `inspected_on`, `name`, `name_en`, `name_mr`, `result` |
| `Milestone` | Milestone | टप्पा | `completed_on`, `due_on`, `name`, `name_en`, `name_mr`, `title` |
| `Road` | Road | रस्ता | `geometry_wkt`, `length_km`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `School` | School | शाळा | `geometry_wkt`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `Toilet` | Toilet | शौचालय | `geometry_wkt`, `name`, `name_en`, `name_mr`, `osm_way_id` |
| `Work` | Work | काम | `category`, `completed_on`, `due_on`, `name`, `name_en`, `name_mr`, `status`, `title` |

## Relationships

| Type | From | To | English | Marathi |
|---|---|---|---|---|
| `ABOUT` | `Gap` | `Node` | about | संबंधित |
| `ALIAS_OF` | `Alias` | `Node` | alias of | चे पर्यायी नाव |
| `AMENDS` | `Corrigendum` | `Tender` | amends | सुधारणा करते |
| `COVERS` | `Post` | `AdminWard` | covers | कार्यक्षेत्र |
| `DIRECTOR_OF` | `Director` | `Company` | director of | चे संचालक |
| `FOR_WORK` | `Contract` | `Work` | for work | कामासाठी |
| `FOR_WORK` | `Penalty` | `Work` | for work | कामासाठी |
| `FOR_WORK` | `Tender` | `Work` | for work | कामासाठी |
| `FOR_YEAR` | `Allocation` | `FiscalYear` | for year | वर्षासाठी |
| `FOR_YEAR` | `Expenditure` | `FiscalYear` | for year | वर्षासाठी |
| `FROM_AWARD` | `Contract` | `Award` | from award | वाटपातून |
| `FUNDED_BY` | `Work` | `Allocation` | funded by | निधी स्रोत |
| `HANDLED_BY` | `IssueType` | `Department` | handled by | द्वारे हाताळले जाते |
| `HAS_DLP` | `Work` | `DefectLiabilityPeriod` | has defect liability period | दोष दायित्व कालावधी आहे |
| `HAS_SLA` | `IssueType` | `ServiceStandard` | has service standard | सेवा मानक |
| `HOLDS` | `Person` | `Post` | holds | धारण करते |
| `IMPOSED_ON` | `Penalty` | `Contractor` | imposed on | यांच्यावर लादलेला |
| `IMPROVES` | `Work` | `Asset` | improves | सुधारणा करते |
| `IN` | `Post` | `Department` | in | मध्ये |
| `IS` | `Contractor` | `Company` | is | म्हणजे |
| `ISSUED_BY` | `Tender` | `Department` | issued by | द्वारे जारी |
| `LOCATED_IN` | `Asset` | `AdminWard` | located in | मध्ये स्थित |
| `OF` | `Award` | `Tender` | award of | निविदेचे वाटप |
| `OF` | `Blacklisting` | `Contractor` | blacklisting of | काळ्या यादीत समावेश |
| `OF` | `Inspection` | `Asset` | inspection of | ची तपासणी |
| `OF` | `Milestone` | `Work` | milestone of | कामाचा टप्पा |
| `ON` | `Bid` | `Tender` | bid on | वरील बोली |
| `OWNS` | `Agency` | `Asset` | owns | मालकीचे |
| `PARENT_OF` | `BudgetHead` | `BudgetHead` | parent of | मूळ शीर्ष |
| `PARTY_TO` | `Contractor` | `Contract` | party to | करारातील पक्षकार |
| `PART_OF` | `Department` | `Agency` | part of | चा भाग |
| `REPORTS_TO` | `Post` | `Post` | reports to | यांना अहवाल देते |
| `REPRESENTS` | `Person` | `ElectoralWard` | represents | प्रतिनिधित्व करते |
| `RETENDER_OF` | `Tender` | `Tender` | retender of | फेरनिविदा |
| `SUBMITTED` | `Contractor` | `Bid` | submitted | सादर केली |
| `TO` | `Award` | `Contractor` | awarded to | यांना वाटप |
| `UNDER` | `Allocation` | `BudgetHead` | under | अंतर्गत |
| `UNDER` | `Expenditure` | `BudgetHead` | under | अंतर्गत |
| `UNDER_CONTRACT` | `Payment` | `Contract` | under contract | कराराअंतर्गत |
| `WITHIN` | `ElectoralWard` | `AdminWard` | within | च्या आत |
| `WITHIN` | `Locality` | `AdminWard` | within | च्या आत |

## Provenance on every fact

| Field | Meaning |
|---|---|
| `source` | SHA-256 of the archived document |
| `page` | Page number, from 1 |
| `quote` | Verbatim words from that page that state the fact |
| `tier` | `official`, `reported`, `citizen` or `derived` |
| `confidence` | 0 to 1 |
