This project was created to measure basic crime statistics of California and its counties.

Location of all data:

Crime statistics: All crime statistics were provided by the California Department of Justice (OpenJustice.gov) through the dataset
  listed as "Arrests." This dataset contains a list of arrests in all of California, grouped by county, listed from 1989 to 2024. 
  This was later cleaned to contain only the data from 2014 to 2024 to be able to better process the data in the dashboard.
  More information about this data set can be found at OpenJustice.gov.

Federal Poverty Income Guideline Grouped by family size: This dataset was provided by the Federal Register and originally cleaned by Jennifer 
  Bumszynski, which was found on the Federal Reserve Economic Data. This dataset contains information on the Federal Poverty Income Guidelines 
  from 1989 to 2026, and the income based on the size of the family. This was later cleaned to only show data from 2014 to 2024, 
  and formatting errors were also fixed so the file could be processed as a CSV file instead of an XLSX file.

Basics of the Dashboard:
Choropleth Map:
  Using a County map of California provided by Caltran's open data portal, a map was created for the Chloropleth to show different
  crimes committed in different counties of California, as well as the year they happened. 
  
Comparison Interactive Graph:
  A graph was created comparing certain crimes committed and the poverty income based on family size, modeled from 2014 to 2024. The number
  of crimes committed is measured on the left-hand side of the graph, while the income of the poverty rate is measured on the right-hand side.

Comparison Interactive Network:
  This graph covers the comparison of race, gender, county, age, and crime type. Modeled as a network graph, you can see the relationship
  between all of these nodes.
