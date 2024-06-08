library(jsonlite)

d <- fromJSON(readChar("output_citation.txt", file.info("output.json")$size))

View(d)
