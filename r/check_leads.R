# Reproduces the desk's lead test in R, independently of the Python code: for every lead in reports/r-check.csv,
# the two-sided tail probability of the observed count under a negative binomial with the desk's mean and size.
# The desk passes when R and Python agree to 1e-9 (relative). Run: Rscript r/check_leads.R reports/r-check.csv
args <- commandArgs(trailingOnly = TRUE)
path <- if (length(args) > 0) args[1] else "reports/r-check.csv"
leads <- read.csv(path, stringsAsFactors = FALSE)
two_sided <- function(y, mu, size) {
  lo <- pnbinom(y, size = size, mu = mu)
  hi <- pnbinom(y - 1, size = size, mu = mu, lower.tail = FALSE)
  pmin(1, 2 * pmin(lo, hi))
}
p_r <- mapply(two_sided, leads$observed, leads$expected, leads$shape)
rel <- abs(p_r - leads$p) / pmax(leads$p, 1e-300)
cat(sprintf("%d leads, largest relative difference %.2e\n", nrow(leads), max(rel)))
# Benjamini-Hochberg in R on the same p-values: which leads would R call strong at the desk's rate?
if (max(rel) > 1e-9) {
  print(leads[rel > 1e-9, ])
  quit(status = 1)
}
