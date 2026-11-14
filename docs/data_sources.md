# Data sources

All data are reported case counts from NCVBDC (National Centre for Vector Borne
Diseases Control), Ministry of Health and Family Welfare, Government of India.

## Dengue: state-wise cases and deaths, 2021-2026
- File: data/raw/dengue_2021_2026_ncvbdc.pdf
- URL: https://ncvbdc.mohfw.gov.in/Doc/Dengue-Cases-deaths-2021-2026-till-April.pdf
- Years used: 2021-2025 (2026 is provisional up to 30 April and is excluded)
- Known issues:
  - West Bengal 2023 and 2024 are partial-year figures (footnoted)
  - West Bengal 2025 is "NR" (not reported)
  - Ladakh is listed as non-endemic (no numbers)
  - Daman & Diu is listed separately from Dadra & Nagar Haveli (merged later)
  - State names are abbreviated differently from the malaria table

## Malaria: state-wise tests, positive cases, Pf cases and deaths, 2022-2026
- File: data/raw/malaria_from2022_ncvbdc.pdf
- URL: https://ncvbdc.mohfw.gov.in/WriteReadData/l892s/97373333991793187283.pdf
- Years used: 2022-2025 (2026 is a partial year and is excluded)
- Column used as "cases": Positive
- Known issues: state names are written differently from the dengue table

## Analysis window
- 2022-2025 for both diseases (dengue 2021 kept as extra history)

## Population (to be added in Step 10)
- Source and year to be recorded when the population file is added