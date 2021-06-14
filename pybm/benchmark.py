import google_benchmark as gbm

@gbm.register
def sum_million(state):
    while state:
        sum(range(10000))

@gbm.register
@gbm.option.range_multiplier(2)
@gbm.option.range(1 << 10, 1 << 18)
@gbm.option.complexity(gbm.oN)
def computing_complexity(state):
    while state:
        sum(range(state.range(0)))
    state.complexity_n = state.range(0)

if __name__ == "__main__":
    gbm.main()