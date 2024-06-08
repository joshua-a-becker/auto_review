library(jsonlite)

d <- fromJSON(readChar("output.json", file.info("output.json")$size))

View(d)
