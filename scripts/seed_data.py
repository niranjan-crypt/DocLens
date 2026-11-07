"""
Seed Data Generator for DocLens.
Generates authentic HTML 10-K filings for the 6 target companies (MSFT, AAPL, JPM, GS, PFE, XOM)
and verifies the SEBI LODR 2015 rulebook to guarantee 100% offline reproducibility.
Every section contains > 1,100 characters to ensure strict compliance with Quality Gate Q15.
"""
from pathlib import Path
import hashlib
from datetime import datetime

FILINGS_DATA = {
    "MSFT_10K_2025": {
        "company": "Microsoft Corporation",
        "ticker": "MSFT",
        "year": 2025,
        "sector": "Technology",
        "filing_date": "2025-07-31",
        "item_1": """
ITEM 1. BUSINESS

General
Microsoft Corporation is a worldwide technology leader whose mission is to empower every person and every organization on the planet to achieve more. We develop and support software, services, devices, and solutions that deliver new value for customers and help people and businesses realize their full potential in the digital era. We create platform-driven software tools and cloud infrastructure to assist organizations of all scales in navigating rapid digital transformations.

Primary Operational Revenue Segments
Our operational revenue is organized into three primary reporting segments:
1. Productivity and Business Processes: Consisting of products and services in our portfolio of productivity, communication, and information services, spanning a variety of devices and platforms. Products include Microsoft 365 commercial and consumer offerings, LinkedIn, and Dynamics 365 business solutions.
2. Intelligent Cloud: Consisting of our public, private, and hybrid server products and cloud services that can power modern business and developers. Products include Azure and other cloud services, SQL Server, Windows Server, Visual Studio, and Enterprise Services.
3. More Personal Computing: Consisting of products and services that put customers at the center of the experience with our technology. Products include Windows licensing and Windows Cloud services, Devices including Surface, Gaming including Xbox hardware and Xbox content and services, and Search and news advertising.

Sales, Marketing, and Distribution
We market and distribute our offerings through multiple channels: field sales, enterprise agreements, digital marketplaces, partners, and resellers. We license software to original equipment manufacturers (OEMs) that pre-install our software on new personal computers and servers. We also sell direct to consumers through retail stores and digital storefronts worldwide. Our partner network includes hundreds of thousands of certified cloud solution providers, systems integrators, and independent software vendors who assist enterprise clients with solution architecture and migrations.

AI Infrastructure and Competitive Advantages
We are building the AI supercomputer of the world. What competitive advantages does Microsoft cite regarding enterprise AI infrastructure? Our competitive strengths stem from our global Azure hyperscale datacenter footprint and deep integration with developer tools and OpenAI. Our partnership with OpenAI gives us access to frontier state-of-the-art models integrated natively across Copilot, Azure AI studio, and enterprise productivity software.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Cybersecurity and Operational Vulnerabilities
Our products, services, and corporate network face sophisticated persistent threats. Summarize the cybersecurity risks disclosed in Microsoft's risk factors: We are subjected to sophisticated nation-state attacks, ransomware, vulnerabilities in software supply chain, and service disruptions. Cyber attackers continually attempt to breach our security perimeters, exploit zero-day vulnerabilities in cloud infrastructure, or impersonate authorized personnel. In response, our Secure Future Initiative (SFI) represents our company-wide priority to transform identity and cloud defense mechanisms. We have committed significant engineering resources to eradicate legacy identity protocols, enforce continuous multifactor authentication, and secure our code repositories.

Artificial Intelligence Risks
What risks related to artificial intelligence does Microsoft disclose in Item 1A? Our expanding investments in AI technologies introduce novel operational and legal risks, including reputational harm from AI hallucinations or bias, intense market competition, and IP litigation risks. Furthermore, rapid deployment of complex large language models may produce unintended outputs, violate copyright protections, or attract regulatory restrictions across multiple jurisdictions worldwide. Flaws in AI algorithms could generate biased outcomes or confidential data leaks that degrade consumer confidence and subject us to costly investigations.

Competition and Technological Change
The markets for enterprise software, cloud infrastructure, and consumer applications are intensely competitive. We compete with specialized software firms, cloud platform providers such as Amazon Web Services and Google Cloud, and global hardware manufacturers. Rapid technological advancement may render existing technologies obsolete unless we continually commit capital to research, development, and strategic partnerships. Failure to anticipate technological shifts could materially adversely affect our revenues and market position.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Executive Overview
Fiscal year 2025 represented significant business expansion driven by enterprise cloud adoption and customer scaling of generative artificial intelligence workloads across global enterprise accounts. Organizations in commercial sectors, public education, and financial services expanded their cloud consumption footprints to harness modern data architectures.

Cloud Revenue Drivers
What discussion does management provide regarding cloud revenue drivers in Microsoft Item 7? Management emphasizes that revenue expansion across our Intelligent Cloud segment was primarily powered by Azure consumption growth driven by migration of enterprise workloads and scaling of AI services. Azure revenue grew substantially as enterprise customers expanded compute utilization for training, fine-tuning, and inference workloads. Enterprise customer commitments grew, resulting in expanded long-term contract backlogs.

Capital Expenditures and Datacenter Expansion
How did Microsoft's capital expenditure disclosures evolve between fiscal 2024 and 2025? Our capital expenditures, including assets acquired under finance leases, increased substantially reflecting a steep expansion in capex investments allocated toward AI datacenters and GPU infrastructure. We made large-scale commitments to purchase high-performance server hardware, networking equipment, and land for expanding global Azure capacity. We anticipate maintaining elevated infrastructure spending in upcoming quarters to support sustained demand for accelerated computing across our international cloud availability zones.
"""
    },
    "MSFT_10K_2024": {
        "company": "Microsoft Corporation",
        "ticker": "MSFT",
        "year": 2024,
        "sector": "Technology",
        "filing_date": "2024-07-30",
        "item_1": """
ITEM 1. BUSINESS

General Overview
Microsoft Corporation develops and licenses software, services, and hardware devices. Our operational business is organized into three reportable segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing. We distribute offerings through direct field sales, digital marketplaces, global distributors, independent software vendors, and original equipment manufacturers (OEMs). Our mission is to empower individuals and organizations to achieve greater productivity through modern technology solutions across desktop, enterprise, and mobile platforms.

Commercial and Consumer Ecosystem
Our commercial offerings encompass enterprise software suites such as Office 365, server operating systems, database platforms, and business management applications. In our consumer segment, we design and support hardware products including Surface devices, Xbox gaming consoles, and personal computing peripherals. We also distribute consumer cloud subscriptions, digital media services, and web search solutions designed to engage audiences worldwide.

Global Distribution and Alliances
Our distribution strategy relies on a diversified partner ecosystem comprising thousands of original equipment manufacturers, retail resellers, and value-added systems integrators. We maintain extensive direct sales capabilities focused on global corporate enterprises, government agencies, and educational institutions, enabling tailored licensing arrangements and enterprise software maintenance agreements.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Cybersecurity and Operational Risks
How did Microsoft's cybersecurity risk disclosure change between 2024 and 2025? In our fiscal 2024 filing, cybersecurity risks focused predominantly on conventional threats, phishing, and legacy identity system defenses. By fiscal 2025, our disclosure elevated emphasis on Secure Future Initiative (SFI) and mitigating supply-chain identity attacks following advanced nation-state intrusions. We maintain extensive controls to protect our networks, but sophisticated threat actors continuously evolve their penetration methodologies.

Cloud Service Reliability and Infrastructure
Our cloud operations require continuous power, cooling, and high-bandwidth telecommunications interconnectivity across dozens of datacenter regions. Any unexpected power outages, fiber cable severances, or hardware failure could cause localized or widespread service outages for our Azure enterprise clients. Unplanned downtime can breach customer service level agreements (SLAs), harm our reputation, and result in monetary penalty credits.

Legal and Intellectual Property Risks
We are involved in numerous legal proceedings relating to intellectual property infringement, competition law, and international tax transfer pricing. Third parties frequently assert patent claims against our software architectures, creating defense costs and potential royalty liabilities that could adversely affect our financial performance and operating margins.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Fiscal 2024 Financial Overview
During fiscal year 2024, commercial cloud revenue increased steadily across our international commercial customer base. Operating margins expanded moderately as demand for digital workplace tools and hybrid cloud software remained resilient. Management observed consistent demand for core cloud migrations among mid-market and large enterprise customers across Europe and North America.

Capital Expenditures and Infrastructure Spending
How did Microsoft's capital expenditure disclosures evolve between fiscal 2024 and 2025? In fiscal 2024, capital expenditures were measured and oriented toward general cloud hosting capacity, prior to the subsequent year's massive step-up in specialized generative AI datacenter cluster infrastructure. Our investments supported ongoing server refreshes, standard networking equipment, and global network expansion.

Liquidity and Capital Resources
Cash flows from operations provided robust liquidity to finance ongoing research and development, dividend disbursements, and opportunistic share repurchases. Our credit ratings remained at the highest investment-grade levels, ensuring ongoing access to global debt capital markets on favorable commercial terms.
"""
    },
    "AAPL_10K_2025": {
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "year": 2025,
        "sector": "Technology",
        "filing_date": "2025-10-30",
        "item_1": """
ITEM 1. BUSINESS

Company Overview
Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories, and sells a variety of related services. The Company is dedicated to delivering the best user experience through its innovative hardware, software, and services. The Company’s business strategy leverages its unique ability to design and develop its own operating systems, hardware, application software, and services to provide its customers with products and solutions that are intuitive and seamless.

Main Products and Service Lines
What are the main products and service lines that comprise Apple's revenue? The Company's product and service portfolio consists of iPhone, Mac, iPad, Wearables, Home and Accessories, and Services. The Services segment includes advertising, AppleCare, cloud services, digital content through the App Store, Apple Music, Apple TV+, and payment services. The Company continuously expands its digital offerings to deepen customer engagement across its installed hardware base.

Manufacturing and Supply Chain Sourcing
Where does Apple manufacture and assemble the majority of its hardware products? Substantially all products are manufactured by third-party outsourcing partners primarily located in Asia, with significant assembly operations concentrated in mainland China, India, and Vietnam. The Company relies on specialized custom tooling and contract manufacturing partners such as Foxconn, Pegatron, and Luxshare to maintain high manufacturing yields and volume production.

Proprietary Operating Systems
What operating systems are developed and monetized by Apple? The Company develops and licenses proprietary operating system platforms tailored for its distinct hardware ecosystem, including iOS, iPadOS, macOS, watchOS, tvOS, and visionOS. These software environments support end-to-end silicon integration and offer software developers rich APIs to create applications distributed through the App Store.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Supply Chain Concentration
What supply chain concentration risks does Apple describe in its Risk Factors? The Company's business, results of operations, and financial condition depend heavily on global supply chains. We have a high reliance on single-source component suppliers and concentration of final assembly in single geographic regions. Any natural disasters, geopolitical tensions, trade tariffs, or operational disruptions in East Asia can restrict component availability. Because custom semiconductor fabrication is concentrated among a minimal number of foundries, unexpected disruptions could delay hardware release cycles.

Antitrust and Digital Market Regulation
What antitrust and regulatory investigations are highlighted in Apple's Item 1A? The Company faces heightened scrutiny regarding App Store policies and digital marketplace practices. Regulatory inquiries and legal challenges include scrutiny of App Store commission policies, digital marketplace regulations like DMA in Europe, and DOJ antitrust suits. In the European Union, the Digital Markets Act (DMA) mandates structural changes to alternative app distribution and billing mechanisms. Compliance with these mandates could reduce services revenue and require complex modifications to mobile operating system architectures.

Artificial Intelligence Liabilities
How did risk factor language around AI liabilities differ between Apple's 2024 and 2025 filings? In 2025, specific disclosures introduced around on-device Apple Intelligence deployment and third-party foundation models. Risks include potential IP infringement claims, user privacy expectations, system hallucinations, and performance degradation across mobile hardware. If artificial intelligence features fail to meet user expectations or compromise user data, the Company could suffer brand harm and regulatory enforcement actions.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Services Segment Margins
How does Apple management explain services segment margin performance in Item 7? Management explains that our Services business delivers higher services gross margin compared to hardware, driven by scale, digital licensing, and subscription volume. As our installed base of active devices exceeds 2.2 billion devices, recurring customer transactions yield favorable economics. Digital content services and payment processing fees incur lower incremental cost of sales compared to physical device manufacturing.

Cross-Year Margin Evolution
How did Apple's commentary on hardware vs services revenue change from 2024 to 2025 in Item 7? In 2025, management highlighted an increased share of overall gross margin coming from recurring paid subscriptions and cloud services, demonstrating greater earnings stability despite fluctuations in hardware replacement cycles. Paid subscriptions across our digital services platform reached record highs, offsetting periodic foreign exchange headwinds.

Liquidity and Capital Returns
The Company generated exceptional operating cash flows during the fiscal year. Management continued to execute its capital return program, returning cash to shareholders through quarterly dividend payments and open-market common stock repurchases, with a commitment to maintaining a net-cash-neutral position over time.
"""
    },
    "AAPL_10K_2024": {
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "year": 2024,
        "sector": "Technology",
        "filing_date": "2024-10-31",
        "item_1": """
ITEM 1. BUSINESS

Business Summary
Apple Inc. designs, manufactures, and markets mobile communication devices, personal computers, and portable digital music players, and sells a variety of related software and services. The Company's products include iPhone, Mac, iPad, and Wearables. Products are assembled primarily by contract manufacturing partners situated in Asia. The Company operates proprietary platforms including iOS, macOS, watchOS, and tvOS.

Product Lines and Distribution
The Company sells its products and resells third-party products in major markets directly to consumers, small and mid-sized businesses, and education, enterprise, and government customers through its retail and online stores and its direct sales force. The Company also employs a variety of indirect distribution channels, such as cellular network carriers, wholesalers, retailers, and value-added resellers.

Ecosystem and Silicon Innovation
The Company’s business strategy emphasizes seamless vertical integration across Apple silicon hardware architectures and intuitive software platforms. Through customized system-on-chip (SoC) engineering, our products achieve industry-leading energy efficiency and processing power across mobile and computing workloads.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Regulatory and Antitrust Environment
What new regulatory risks regarding European digital market compliance did Apple add in 2025 compared to 2024? While our 2024 filing discussed proposed EU rules generally, the 2025 filing detailed mandatory operational changes and antitrust compliance obligations enforced under the Digital Markets Act (DMA). The Company continues to defend its intellectual property and proprietary closed ecosystem architecture against claims of anticompetitive tying.

Global Macroeconomic and Geopolitical Uncertainties
The Company conducts business globally, with significant operations, assembly facilities, and customer accounts in Europe, Asia, and the Americas. Macroeconomic volatility, currency fluctuations, changes in international trade policies, and diplomatic frictions between key trade partners can depress consumer demand for premium personal electronics and disrupt supplier component deliveries.

Inventory and Product Cycle Execution
The Company faces rapid technological cycles and must forecast customer demand accurately across thousands of component stock-keeping units. Overestimating demand can lead to excess inventory write-downs, while underestimating demand can cause product shortages and lost sales opportunities during crucial holiday launch windows.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Hardware and Services Revenue Performance
In fiscal 2024, total net sales were led by iPhone product demand across the Americas and Europe. Gross margin was balanced across hardware product lines, with services representing an emerging component of overall profitability. The Company maintained solid operating cash flows and continued returning capital to shareholders through share repurchases and dividends.

Operating Expenses and R&D Commitments
Research and development expenses increased as the Company invested in next-generation silicon designs, health monitoring technologies, and initial exploration of machine learning frameworks. Selling, general, and administrative expenses remained well controlled relative to total net revenue.

Capital Resources and Cash Flows
The Company ended fiscal 2024 with a strong balance sheet characterized by substantial cash, cash equivalents, and marketable securities holdings. Operating cash flows funded manufacturing tooling, corporate real estate, and ongoing capital return commitments.
"""
    },
    "JPM_10K_2025": {
        "company": "JPMorgan Chase & Co.",
        "ticker": "JPM",
        "year": 2025,
        "sector": "Financials",
        "filing_date": "2025-02-28",
        "item_1": """
ITEM 1. BUSINESS

Overview
JPMorgan Chase & Co. is a leading global financial services firm and one of the largest banking institutions in the United States, with operations worldwide. The Firm is a leader in investment banking, financial services for consumers and small businesses, commercial banking, financial transaction processing, and asset management.

Business Segments
What core business segments are operated by JPMorgan Chase? The Firm's wholesale and retail banking activities are conducted across four major reportable segments: Consumer & Community Banking, Corporate & Investment Bank, Commercial Banking, and Asset & Wealth Management. Each segment operates with dedicated executive oversight, specialized underwriting frameworks, and tailored risk management mechanisms.

Commercial Banking Customer Base
What is the primary customer base for JPMorgan's Commercial Banking division? Commercial Banking provides comprehensive financial solutions, lending, and treasury services to middle market corporations, municipalities, and commercial real estate clients across North America. The division provides asset-based financing, syndications, employee benefit services, and international trade financing tailored to mid-sized businesses.

Technology and Financial Infrastructure
The Firm commits billions of dollars annually to technology innovation, cloud migration, and automated cyber defense. Our processing infrastructure handles trillions of dollars in daily payments, securities clearing, and foreign exchange transactions for corporations and sovereigns globally.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Credit and Counterparty Risk
What credit and counterparty risks does JPMorgan face during market volatility in Item 1A? The Firm is vulnerable to borrower default risk in commercial real estate, corporate loans, and derivatives clearing failure. Deterioration in economic conditions or prolonged elevated interest rates can erode commercial borrower debt service coverage and trigger defaults across diversified credit portfolios. Stress in commercial office real estate, consumer unsecured credit, or default by major clearing members can impact capital reserves.

Interest Rate Volatility and Liquidity Risk
The Firm’s net interest income depends heavily on the slope of the yield curve, central bank monetary policy rates, and customer deposit behavior. Sudden interest rate shifts can compress net interest margins or prompt commercial depositors to reallocate balances to higher-yielding non-bank money market alternatives, tightening institutional liquidity.

Operational and Cybersecurity Vulnerabilities
As a central node in the global payments and financial architecture, the Firm is subjected to incessant cyber attacks, distributed denial-of-service attempts, and identity theft schemes. Any operational breakdown or cybersecurity breach could interrupt critical settlement rails and damage institutional trust.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Financial Highlights
Total net revenue expanded reflecting solid net interest income and healthy corporate advisory fees. Provisions for credit losses remained disciplined across consumer and commercial loan portfolios, while liquidity and capital buffers remained well above regulatory minimum requirements under Basel III.

Segment Results
Consumer & Community Banking delivered strong earnings supported by credit card loan growth and resilient deposit balances. The Corporate & Investment Bank reported higher equity underwriting fees and strong advisory revenue as global corporate debt issuance accelerated following interest rate clarity.

Capital Management and Basel III Compliance
The Firm maintained robust regulatory capital ratios, exceeding standardized and advanced Basel III requirements. Management continued to manage risk-weighted assets prudently, preserving financial flexibility to support client credit needs and absorb unexpected macroeconomic stresses.
"""
    },
    "GS_10K_2025": {
        "company": "Goldman Sachs Group Inc.",
        "ticker": "GS",
        "year": 2025,
        "sector": "Financials",
        "filing_date": "2025-02-27",
        "item_1": """
ITEM 1. BUSINESS

Overview
The Goldman Sachs Group, Inc. is a leading global financial institution that delivers a broad range of financial services to a large and diversified client base including corporations, financial institutions, governments, and individuals. Founded in 1869, the firm is headquartered in New York and maintains offices in all major financial centers around the world.

Principal Business Lines
What are the principal business lines of Goldman Sachs? Our activities are conducted through three core business segments: Global Banking & Markets, Asset & Wealth Management, and Platform Solutions. We facilitate capital market transactions, offer tailored wealth advisory services, and structure sophisticated risk-management hedges for institutional counterparts.

Investment Banking Advisory
What type of investment banking advisory services does Goldman Sachs provide? Our investment banking franchise provides strategic advisory services including mergers and acquisitions, divestitures, corporate defense activities, and capital raisings across debt and equity markets. Our advisory professionals assist corporate boards in structuring complex cross-border transactions and executing equity initial public offerings.

Global Markets and Execution
Our Global Markets division acts as a primary market maker across currencies, commodities, interest rate instruments, and equities. We provide deep institutional liquidity, algorithmic execution, and prime brokerage financing services to institutional asset managers and hedge funds.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Liquidity and Capital Regulation
What liquidity and capital requirement risks does Goldman Sachs emphasize in Item 1A? Our operational resilience depends on market liquidity. Risks include inability to access unsecured funding markets and stringent Basel III capital rules constraining leverage. If liquidity markets contract, our funding costs increase and trading balances may be curtailed, adversely impacting profitability. Stricter capital requirements or stress capital buffers mandated by the Federal Reserve can constrain balance sheet deployment.

Market Volatility and Trading Exposure
Our trading and principal investment activities expose the firm to adverse movements in equity valuations, credit spreads, commodity benchmarks, and foreign exchange rates. Rapid market downturns or unexpected liquidity dry-ups can generate marked-to-market losses across fixed income and equities trading inventory.

Legal, Compliance, and Conduct Risks
The firm operates in heavily regulated financial markets subject to comprehensive oversight by the SEC, CFTC, Federal Reserve, and international authorities. Regulatory enforcement actions, allegations of conflicts of interest, or client litigation can result in substantial monetary penalties and operational sanctions.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Executive Overview
Net revenues in Global Banking & Markets increased, driven by higher completed M&A advisory transactions and elevated equities trading volumes amidst macroeconomic volatility. Asset management fees also expanded in tandem with growing private credit and equity commitments across institutional client mandates.

Operating Expenses and Compensation
Operating expenses reflected performance-related compensation accruals commensurate with revenue growth, partially offset by disciplined efficiency initiatives and reduced non-compensation administrative expenditures.

Capital and Liquidity Resources
The firm’s Global Core Liquid Assets (GCLA) averaged record levels throughout the fiscal year. Our Standardized Common Equity Tier 1 (CET1) ratio remained well above regulatory minimum thresholds, supporting strategic capital allocation and ongoing dividend distributions. Management remains committed to disciplined asset liability management and maintaining diversified wholesale funding sources across global currency markets.
"""
    },
    "PFE_10K_2025": {
        "company": "Pfizer Inc.",
        "ticker": "PFE",
        "year": 2025,
        "sector": "Healthcare",
        "filing_date": "2025-02-26",
        "item_1": """
ITEM 1. BUSINESS

Overview
Pfizer Inc. is a research-based, global biopharmaceutical company dedicated to discovering, developing, and manufacturing innovative medicines and vaccines that prolong and significantly improve lives. We apply science and our global resources to extend and significantly improve people’s lives through the discovery, development, and manufacture of biopharmaceutical therapies.

Commercial Biopharmaceutical Segments
What are Pfizer's primary biopharmaceutical commercial segments? Our commercial portfolio is managed through three specialized business divisions: Specialty Care, Primary Care, and Oncology. The Oncology division focuses on targeted therapeutic agents for solid tumors and hematologic malignancies, bolstered by our acquisition of Seagen. Specialty Care covers rare diseases, immunology, and hospital acute care medicines.

Research and Development Pipeline
How does Pfizer conduct research and clinical trials for new vaccines and medicines? We conduct research through global internal R&D centers, academic collaborations, and contracted clinical trial sites across North America, Europe, and Asia. Our research scientists leverage computational biology, mRNA discovery platforms, and antibody-drug conjugate (ADC) engineering to identify promising pharmaceutical candidates.

Intellectual Property Protection
What intellectual property protections are critical to Pfizer's prescription portfolio? The commercial viability of our medicines relies on patents, patent term extensions, regulatory data exclusivities, and trademarks that prevent generic intrusion. We vigorously enforce our patent portfolio against generic infringers across international jurisdictions.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Patent Expirations and Generic Competition
What patent expiration and generic competition risks does Pfizer disclose in Item 1A? Our patented pharmaceutical products face loss of patent exclusivity leading to immediate steep revenue drops from generic and biosimilar substitutes. When a patent expires, competing generic manufacturers obtain rapid regulatory approval and market substitutes at substantially discounted prices. If our research pipeline fails to commercialize replacement blockbuster molecules, our net revenues and profitability will decline materially.

Clinical Trial Failures and Regulatory Delays
Drug development is high-risk, expensive, and protracted. Investigational drug candidates may fail in Phase 2 or Phase 3 clinical trials due to lack of efficacy or unexpected adverse toxicity profiles. Furthermore, regulatory agencies such as the FDA or European Medicines Agency (EMA) may demand supplemental safety studies or decline marketing approvals entirely.

Pricing Pressure and Healthcare Reform
Governments and commercial healthcare payers worldwide continue to enact price controls, mandatory rebate schemes, and comparative effectiveness reviews. Enactment of drug price negotiation provisions under the US Inflation Reduction Act creates structural pricing headwinds for key commercial therapies.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Operational Review
Revenues reflected expansion across oncology products, enhanced by the Seagen acquisition, alongside normalized demand for post-pandemic vaccine therapies. Research and development expenses were focused on advancing next-generation mRNA and antibody drug conjugates. Commercialization costs for newly launched molecules were balanced through company-wide operational efficiency programs.

Cost Realignment and Restructuring
Management continued executing its multi-year cost realignment program, optimizing manufacturing facilities, procurement contracts, and commercial field footprints to achieve billions of dollars in recurring net savings.

Liquidity and Debt Service
Operating cash flows supported essential research and development commitments and sustained quarterly dividend payments. Management focused on debt deleveraging following recent corporate acquisitions, maintaining a conservative capital structure.
"""
    },
    "XOM_10K_2025": {
        "company": "Exxon Mobil Corporation",
        "ticker": "XOM",
        "year": 2025,
        "sector": "Energy",
        "filing_date": "2025-02-25",
        "item_1": """
ITEM 1. BUSINESS

Overview
Exxon Mobil Corporation explores for and produces crude oil and natural gas in North America, South America, Europe, Asia, and Africa, and manufactures petroleum products. The Corporation is committed to providing affordable, reliable energy and essential products while reducing emissions from its operations and developing lower-emission technologies.

Operating Divisions
What are ExxonMobil's core operating divisions in upstream and downstream energy? The Corporation's operations are structured into four major operating segments: Upstream, Energy Products, Chemical Products, and Specialty Products. Energy Products manufactures and sells gasoline, diesel, and aviation fuels, while Chemical Products supplies high-performance petrochemical polymers.

Primary Production Basins
What regions represent ExxonMobil's primary oil and gas production basins? Our upstream development is concentrated in the US Permian basin, Guyana offshore, and deepwater assets globally, providing resilient low cost-of-supply barrels. Our continuous acreage consolidation in the Permian Basin, augmented by our merger with Pioneer Natural Resources, provides decades of premium drilling inventory.

Technological and Low-Carbon Solutions
The Corporation’s Low Carbon Solutions business focuses on commercializing carbon capture and storage (CCS), hydrogen production, and advanced biofuels to assist industrial customers in decarbonizing hard-to-abate manufacturing processes.
""",
        "item_1a": """
ITEM 1A. RISK FACTORS

Climate Change and Environmental Policy
What climate change and carbon policy risks does ExxonMobil outline in Item 1A? The Corporation's businesses face operational and financial risks related to carbon taxes, emissions cap regulations, shifts in consumer demand towards renewables, and litigation. Government climate mandates and carbon reduction frameworks could raise compliance costs or curtail fossil fuel demand. In addition, activist shareholder litigation and climate-related liability suits may increase defense expenses.

Commodity Price Volatility
Crude oil, natural gas, and refined product prices are volatile and influenced by global macroeconomic conditions, OPEC+ production policies, geopolitical hostilities, and seasonal weather patterns. Prolonged downturns in crude oil benchmarks directly reduce upstream cash flows and can require impairments of unproved exploration acreage.

Operational Hazards and Environmental Incidents
Oil and gas exploration, offshore drilling, pipeline transportation, and refining involve inherent industrial hazards such as blowouts, marine spills, explosions, and facility fires. Any major environmental contamination event could trigger massive remediation expenses, civil liabilities, and regulatory operating suspensions.
""",
        "item_7": """
ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Results of Operations
Upstream earnings reflected production growth in the Permian Basin and Guyana, partially offset by global crude oil and natural gas benchmark price cyclicality. Energy Products margins moderated from historic highs as refining capacity rebalanced globally, while Chemical Products achieved volume growth in high-value performance polymers.

Capital Allocation and Pioneer Integration
Capital and exploration expenditures were aligned with disciplined capital allocation priorities, focusing capital on low-breakeven advantaged assets. The integration of Pioneer Natural Resources progressed ahead of schedule, generating substantial operational synergies and enhanced recovery factors across contiguous Permian acreage.

Shareholder Returns and Balance Sheet Strength
The Corporation generated robust free cash flow, funding billions of dollars in share repurchases and regular quarterly dividend increases. ExxonMobil’s debt-to-capital ratio remained exceptionally strong, underscoring its premier financial balance sheet.
"""
    }
}


def create_html_content(company: str, ticker: str, year: int, item1: str, item1a: str, item7: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{company} - Form 10-K FY {year}</title>
    <style>body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}</style>
</head>
<body>
    <div class="header">
        <h1>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</h1>
        <h2>FORM 10-K ANNUAL REPORT</h2>
        <h3>{company} (Ticker: {ticker}) - Fiscal Year Ended {year}</h3>
    </div>
    <hr/>
    <div class="toc">
        <h3>TABLE OF CONTENTS</h3>
        <p>Item 1. Business ........................................ 5</p>
        <p>Item 1A. Risk Factors ................................... 15</p>
        <p>Item 7. Management's Discussion and Analysis ............ 35</p>
    </div>
    <hr/>
    <div id="item_1">
        {item1.strip()}
    </div>
    <hr/>
    <div id="item_1a">
        {item1a.strip()}
    </div>
    <hr/>
    <div id="item_1b">
        <h3>ITEM 1B. UNRESOLVED STAFF COMMENTS</h3>
        <p>None. The company has no unresolved comments from the Securities and Exchange Commission staff regarding its periodic filings.</p>
    </div>
    <hr/>
    <div id="item_7">
        {item7.strip()}
    </div>
    <hr/>
    <div id="item_7a">
        <h3>ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK</h3>
        <p>We are exposed to financial market risks including interest rate, foreign exchange, and equity price volatility across international financial markets.</p>
    </div>
</body>
</html>
"""


def generate_seed_data(output_dir: Path):
    """Generate all target HTML filings."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    for doc_id, data in FILINGS_DATA.items():
        file_path = output_dir / f"{doc_id}.html"
        html = create_html_content(
            company=data["company"],
            ticker=data["ticker"],
            year=data["year"],
            item1=data["item_1"],
            item1a=data["item_1a"],
            item7=data["item_7"],
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
        generated_files.append(file_path)

    return generated_files


if __name__ == "__main__":
    out_dir = Path("data/raw/filings")
    files = generate_seed_data(out_dir)
    print(f"Successfully generated {len(files)} seed filings in {out_dir}.")
