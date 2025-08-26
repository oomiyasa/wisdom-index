# Community Switching Guide - Multi-Mode Harvesting

## Quick Community Switches

### 🏥 Medical Administration & Office Ops
```yaml
# Update in wi_config_unified.yaml
industry_modifiers:
  - Medical
  - Healthcare
  - Administration
  - Office
  - Billing
  - Coding
  - Scheduling
  - EMR
  - EHR
  - Practice
  - Hospital
  - Insurance
  - Claims
  - Clinical
  - Patient
  - Revenue
  - Operations

keywords:
  # ... existing keywords ...
  - medical_tip
  - healthcare_tip
  - admin_tip
  - office_tip
  - billing_tip
  - coding_tip
  - scheduling_tip
  - emr_tip
  - ehr_tip
  - practice_tip
  - hospital_tip
  - insurance_tip
  - claims_tip
  - clinical_tip
  - patient_tip
  - revenue_tip
  - operations_tip

reddit:
  subreddits:
    - medicaloffice
    - medicalbilling
    - medicalcoding
    - HealthIT
    - epic
    - nursing
    - medicalassistants
    - pharmacytechnician
    - PracticeManagement
    - hospitaladministration
    - healthcareadministration
    - Insurance
    - medicalschool
```

### 💰 Financial Advisory & Service Advisor
```yaml
industry_modifiers:
  - Financial
  - Advisory
  - Service
  - Advisor
  - Planning
  - Investment
  - Wealth
  - Client
  - Portfolio
  - Risk
  - Compliance
  - Business
  - Consulting
  - Strategy

keywords:
  # ... existing keywords ...
  - financial_tip
  - advisory_tip
  - service_tip
  - advisor_tip
  - planning_tip
  - investment_tip
  - wealth_tip
  - client_tip
  - portfolio_tip
  - risk_tip
  - compliance_tip
  - business_tip
  - consulting_tip
  - strategy_tip

reddit:
  subreddits:
    - financialadvisortips
    - fpanda
    - financialmodeling
    - serviceadvisors
```

### 🔨 Contractor/Trade Communities
```yaml
industry_modifiers:
  - Contractor
  - Trade
  - Construction
  - HVAC
  - Electrical
  - Plumbing
  - Carpentry
  - Masonry
  - Roofing
  - Landscaping
  - Home
  - Improvement
  - DIY
  - Project
  - Client
  - Business

keywords:
  # ... existing keywords ...
  - contractor_tip
  - trade_tip
  - construction_tip
  - hvac_tip
  - electrical_tip
  - plumbing_tip
  - carpentry_tip
  - masonry_tip
  - roofing_tip
  - landscaping_tip
  - home_tip
  - improvement_tip
  - diy_tip
  - project_tip
  - client_tip
  - business_tip

reddit:
  subreddits:
    - HVAC
    - electricians
    - Plumbing
    - Construction
    - contractors
    - carpentry
    - masonry
    - roofing
    - landscaping
    - homeimprovement
    - diy
    - construction
```

### 🧪 Laboratory/QA Communities
```yaml
industry_modifiers:
  - Laboratory
  - Lab
  - Research
  - Science
  - Quality
  - Assurance
  - Testing
  - Validation
  - Compliance
  - Regulatory
  - GMP
  - GLP
  - FDA
  - ISO
  - Biotechnology
  - Pharmaceutical
  - Medical
  - Clinical

keywords:
  # ... existing keywords ...
  - lab_tip
  - laboratory_tip
  - research_tip
  - science_tip
  - quality_tip
  - assurance_tip
  - testing_tip
  - validation_tip
  - compliance_tip
  - regulatory_tip
  - gmp_tip
  - glp_tip
  - fda_tip
  - iso_tip
  - protocol_tip
  - procedure_tip
  - method_tip
  - standard_tip
  - audit_tip
  - documentation_tip

reddit:
  subreddits:
    - labrats
    - qualityassurance
```

### 💻 IT/Systems Administration
```yaml
industry_modifiers:
  - IT
  - Systems
  - Administration
  - Technology
  - Infrastructure
  - Support
  - Operations
  - DevOps
  - Cloud
  - Security
  - Network
  - Database
  - CRM
  - Salesforce
  - Revenue
  - Operations
  - Business
  - Enterprise

keywords:
  # ... existing keywords ...
  - it_tip
  - sysadmin_tip
  - systems_tip
  - technology_tip
  - infrastructure_tip
  - support_tip
  - operations_tip
  - devops_tip
  - cloud_tip
  - security_tip
  - network_tip
  - database_tip
  - crm_tip
  - salesforce_tip
  - revenue_tip
  - revops_tip
  - business_tip
  - enterprise_tip

reddit:
  subreddits:
    - sysadmin
    - techsupportgore
    - salesforce
    - revops
```

### 🚀 SaaS (Current)
```yaml
industry_modifiers:
  - SaaS
  - Software
  - Startup
  - Business
  - Product
  - Marketing
  - Sales
  - Customer
  - Growth
  - Revenue
  - Operations
  - Technology
  - Platform
  - Service
  - Subscription
  - Enterprise
  - B2B
  - B2C

keywords:
  # ... existing keywords ...
  - saas_tip
  - software_tip
  - startup_tip
  - business_tip
  - product_tip
  - marketing_tip
  - sales_tip
  - customer_tip
  - growth_tip
  - revenue_tip
  - operations_tip
  - technology_tip
  - platform_tip
  - service_tip
  - subscription_tip
  - enterprise_tip
  - b2b_tip
  - b2c_tip

reddit:
  subreddits:
    - saas
```

## Usage Instructions

1. **Choose your target community** from the list above
2. **Update the configuration** in `wi_config_unified.yaml`:
   - Replace `industry_modifiers` section
   - Replace `keywords` section (add the community-specific tips)
   - Replace `reddit.subreddits` section
3. **Run the harvest**: `python3 harvester_main.py --config wi_config_unified.yaml`
4. **Filter and transform**: Follow the standard workflow

## Multi-Mode Harvesting Benefits

✅ **Evergreen keyword search** - Finds tacit knowledge across all time
✅ **Annual top posts** - Recent high-quality content  
✅ **Fresh new posts** - Latest insights and discussions
✅ **Controversial posts** - "What not to do" insights
✅ **Enhanced comment harvesting** - Confidence-based sorting with keyword boosting
✅ **Quality filtering** - Balanced thresholds for optimal results

## Expected Results

- **Harvest**: 100-150 items per community
- **Quality filter**: 70-80% retention rate
- **Wisdom transformation**: 30-50% retention rate
- **Final insights**: 20-40 high-quality tacit knowledge items per community
