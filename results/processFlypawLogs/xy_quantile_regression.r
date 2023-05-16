library("quantreg")
csv_data <- read.csv("power_distance_scatter.txt")
X <- csv_data$distance
Y <- csv_data$power
highconf <- .75
lowconf <- .25
appreq <- 12.5

hperc <- sprintf("%d%% Quantile", highconf*100)
lperc <- sprintf("%d%% Quantile", lowconf*100)

plot(Y ~ X, xlab = "Distance (m)", ylab = "Power (dB)", main = "Radio Signal Power vs Transmitter Distance")
#aerpaw.eq <- Y ~ a * X^2 + b * X + c
#aerpaw.start <- list(a = 2, b = 3, c = 5)
#aerpaw.eq <- Y ~ a/(1+exp(-(X-c)/b))
#aerpaw.start <- list(a = 0.5, b = 1, c = 50)
modh <- rq(Y ~ log(X), data=csv_data, tau = highconf)
#modh <- nls(aerpaw.eq, data = csv_data, start = aerpaw.start)
pDFh <- data.frame(X = seq(1, 500, length = 100))
pDFh <- within(pDFh, Y <- predict(modh, newdata = pDFh))
lines(Y ~ X, data = pDFh, col = "green", lwd = 3)
modl <- rq(Y ~ log(X), data=csv_data, tau = lowconf)
#modl <- nls(aerpaw.eq, data = csv_data, start = aerpaw.start, tau=.25)
pDFl <- data.frame(X = seq(1, 500, length = 100))
pDFl <- within(pDFl, Y <- predict(modl, newdata = pDFl))
lines(Y ~ X, data = pDFl, col = "red", lwd = 3)
mod <- rq(Y ~ log(X), data=csv_data, tau = .5)
#mod <- nls(aerpaw.eq, data = csv_data, start = aerpaw.start, tau=.5)
pDF <- data.frame(X = seq(1, 500, length = 100))
pDF <- within(pDF, Y <- predict(mod, newdata = pDF))
lines(Y ~ X, data = pDF, col = "blue", lwd = 3)
appreq_mod <- data.frame(X = seq(1, 500, length = 100))
appreq_mod <- within(appreq_mod, Y <- appreq)
lines(Y ~ X, data = appreq_mod, col = "orange", lwd = 3)
#need to calculate app req line intercepts automatically... manual for now
app_int_h <- data.frame(Y = seq(-30, 28, length = 100), X = seq(45,45, length = 100))
lines(Y ~ X, data = app_int_h, col = "red", lwd = 3, lty = 2)
app_int_l <- data.frame(Y = seq(-30, 28, length = 100), X = seq(82,82, length = 100))
lines(Y ~ X, data = app_int_l, col = "green", lwd = 3, lty = 2)
legend("bottomleft", legend=c(hperc, lperc, "Median Power", "Application Requirement", "High End Limit", "Low End Limit"), col=c("green","red","blue","orange","red","green"), lty=c(1,1,1,1,2,2), lwd=c(2,2,2,2,2,2), cex=0.8)