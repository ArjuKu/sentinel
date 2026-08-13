OFAC_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"
OFAC_SDN_LEGACY_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OFAC_SDN_ALT_URL = "https://www.treasury.gov/ofac/downloads/alt.csv"

OFAC_NON_SDN_URL = "https://www.treasury.gov/ofac/downloads/consolidated/cons_prim.csv"
OFAC_NON_SDN_ALT_URL = "https://www.treasury.gov/ofac/downloads/consolidated/cons_alt.csv"

UN_CONSOLIDATED_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

DFAT_LANDING_URL = "https://www.dfat.gov.au/international-relations/security/sanctions/consolidated-list"

MAS_DESIGNATED_URL = "https://www.mas.gov.sg/regulation/anti-money-laundering/targeted-financial-sanctions/lists-of-designated-individuals-and-entities"

MAS_ENFORCEMENT_URL = "https://www.mas.gov.sg/regulation/enforcement/enforcement-actions"
MAS_ENFORCEMENT_API_URL = "https://www.mas.gov.sg/api/v1/enforcementsearch"

MAS_INVESTOR_ALERT_URL = "https://www.mas.gov.sg/api/v1/ialsearch"

TSFA_URL = "https://sso.agc.gov.sg/Act/TSFA2002?ProvIds=Sc1-"

FUZZY_THRESHOLD = 85
HIT_THRESHOLD = 95
POTENTIAL_THRESHOLD = 80

USER_AGENT = "SENTINEL-Screener/1.0"
REQUEST_TIMEOUT = 30
REQUEST_RETRIES = 2
REQUEST_BACKOFF = 1.0
DFAT_TIMEOUT = 20

SOURCES = [
    "ofac_sdn",
    "ofac_non_sdn",
    "un_consolidated",
    "dfat",
    "mas_designated",
    "mas_enforcement",
    "tsfa",
    "mas_investor_alert",
]

SOURCE_LABELS = {
    "ofac_sdn": "OFAC SDN List",
    "ofac_non_sdn": "OFAC Non-SDN List",
    "un_consolidated": "UN Consolidated List",
    "dfat": "Australian DFAT List",
    "mas_designated": "MAS Designated Lists",
    "mas_enforcement": "MAS Enforcement Actions",
    "tsfa": "SG TSFA First Schedule",
    "mas_investor_alert": "MAS Investor Alert List",
}

SOURCE_URLS = {
    "ofac_sdn": "https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list",
    "ofac_non_sdn": "https://ofac.treasury.gov/consolidated-sanctions-list-non-sdn-list",
    "un_consolidated": "https://scsanctions.un.org/",
    "dfat": "https://www.dfat.gov.au/international-relations/security/sanctions/consolidated-list",
    "mas_designated": "https://www.mas.gov.sg/regulation/anti-money-laundering/targeted-financial-sanctions/lists-of-designated-individuals-and-entities",
    "mas_enforcement": "https://www.mas.gov.sg/regulation/enforcement/enforcement-actions",
    "tsfa": "https://sso.agc.gov.sg/Act/TSFA2002?ProvIds=Sc1-",
    "mas_investor_alert": "https://www.mas.gov.sg/investor-alert-list",
}

COLORS = {
    "bg_primary": "#FFFFFF",
    "text_primary": "#111111",
    "accent_yellow": "#E5A913",
    "btn_secondary": "#F5F5F5",
    "border_secondary": "#333333",
}
