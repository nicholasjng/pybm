# pybm example #1: "Hello, math world!"

This markdown contains a walkthrough for the inaugural pybm example, `sum`. It
is meant to display the usefulness of pybm in the context of Python library
development, where usually only a single implementation of a function is
maintained; therefore, especially in performance-critical sections, usually the
most optimized algorithm and implementation should be used.

## Prerequisites

Please navigate to a folder suitable to you and clone into the pybm sum example
repository:

```shell
git clone https://github.com/nicholasjng/pybm-sum-example.git
cd pybm-sum-example
git checkout master
```

You need to run any pybm commands from a virtual environment with pybm
installed. The easiest way to do this is with the following series of commands:

```
# you should be in the root of the pybm-sum-example repository now

python3 -m venv venv/
source venv/bin/activate
python -m pip install git+https://github.com/nicholasjng/pybm

# initialize pybm with a configuration and environment file
pybm init
```

## Setting the stage

We put ourselves in the perspective of the author of a fictitous Python math
library. As any good math package would require, there also has to be a
`sum` function, calculating the sum of the first `n` natural numbers for a given
integer input `n`. Currently, our author solved it like this:

```python
def my_sum(n: int):
    result = 0
    for i in range(1, n + 1):
        for _ in range(i):
            result += 1

    return result
```

The code speaks volumes: The sum of the first `n` numbers is just the number 1
repeated `n` times. Not terribly clever, yet of course correct. But as you
notice, the computation is really tedious: A nested loop, with constant
increments of 1, each time.

In fact, this code is pretty much a complete catastrophe: Our function has
_quadratic_ complexity, meaning that the computational workload scales with the
square of the input. Without even running it, we can assume that this will not
behave very well when users want to compute sums of large numbers. Can we do
better?

## Reducing it to linear time

Alright, maybe the improvement here is already too obvious. Of course, we can
easily cut the complexity by summing the actual numbers instead of ones. The new
functions then looks like this:

```python
def my_sum(n: int):
    result = 0
    for i in range(1, n + 1):
        result += i

    return result
```

But we need to adhere to a normal development workflow here! So instead of just
hacking the new algorithm and pushing the changes, we need to create a feature
branch (we're calling it "linear-time"), containing our improved algorithm. The
branch is already present in the example repository that you previously checked
out. You can create a pybm benchmark environment for it with the following
command, run from the repository root folder on `master`:

```shell
pybm env create linear-time

Creating benchmark environment for git ref 'linear-time'.
Adding worktree for ref 'linear-time' in directory ~/Workspaces/python/sum-example@linear-time.....done.
Creating virtual environment in directory ~/Workspaces/python/sum-example@linear-time/venv.....done.
Installing packages git+https://github.com/nicholasjng/pybm into virtual environment in location ~/Workspaces/python/sum-example@linear-time/venv.....done.
Successfully installed packages git+https://github.com/nicholasjng/pybm into virtual environment in location ~/Workspaces/python/sum-example@linear-time/venv.
Successfully created benchmark environment for ref 'linear-time'.
```

This checks out the HEAD of the branch "linear-time" into a separate git
worktree located in the parent folder of the repository, and creates a fresh
Python virtual environment for it.

But everything changes once we pick up an analysis textbook!

## The super speedy sum, after C. F. Gauss

At first glance, calculating a sum of `n` numbers looks like an inherently
linear problem. Yet, the mathematical problem contains so much hidden structure
that we can actually do it for any number `n` on a sheet of paper. The proof is
standard for any first-semester analysis course in university mathematics, and
sometimes finds its way into school curricula as well.

In Germany specifically, it floats around as a nice little anecdote from the
early childhood of
[Carl Friedrich Gauss](https://en.wikipedia.org/wiki/Carl_Friedrich_Gauss),
commonly viewed as one of the greatest mathematicians of all time, who,
according to legend, used it to solve the summation of the first 100 numbers in
a matter of seconds, much faster than his fellow pupils. There is a nice
[article](https://de.wikipedia.org/wiki/Gau%C3%9Fsche_Summenformel) on German
Wikipedia on it as well.

The implementation is quite literally a one-liner, and looks like this:

```python
def my_sum(n: int):
    return n * (n + 1) // 2
```

No more loops, no `if`s, no buts: We have reduced the summation problem to a
_constant time_ problem! This looks very promising. Again, this algorithm is
already implemented on another branch called `constant-time`, for which we can
also create a benchmark environment:

```shell
pybm env create constant-time

Creating benchmark environment for git ref 'constant-time'.
Adding worktree for ref 'constant-time' in directory ~/Workspaces/python/sum-example@constant-time.....done.
Creating virtual environment in directory ~/Workspaces/python/sum-example@constant-time/venv.....done.
Installing packages git+https://github.com/nicholasjng/pybm into virtual environment in location ~/Workspaces/python/sum-example@constant-time/venv.....done.
Successfully installed packages git+https://github.com/nicholasjng/pybm into virtual environment in location ~/Workspaces/python/sum-example@constant-time/venv.
Successfully created benchmark environment for ref 'constant-time'.
```

Now we are left with a high-noon situation: Three implementation candidates,
three different algorithms, only one can be added to our math library. But what
are the numbers? We want to make an **informed decision** and find our best
performer in a scientific manner. That's where a benchmark helps!

## Running the benchmark

This is the perfect situation for pybm! We have environments for all of our
algorithms (our master branch is also contained in a benchmark environment
called "root", created during `pybm init`), so we can directly compare them. We
do this by writing a very basic benchmark test:

```python
# benchmarks/sum.py
import os
import sys

import pybm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from main import my_sum


def f():
    return my_sum(10000)


if __name__ == "__main__":
    pybm.run(context=globals())
```

Aside from some sys-path-hacking to get the python path set up correctly, the
test file is very simple: We import our function `my_sum`, sum up all numbers
from 1 to 10000, and run the benchmark when running the module as `__main__`.
Everything else is set up by pybm's default configuration, so we do not need to
tweak more options and spend more time to get up and running.

NOTE: The above benchmark file is the same on all three branches, and there is a
good reason for it! When comparing the different implementations, we do need the
benchmarking procedure to stay the same.

```shell
# Tell pybm to run the benchmarks in the benchmarks directory in all environments.
pybm run benchmarks/ --all

Starting benchmarking run in environment 'root'.
Discovering benchmark targets in environment 'root'.....done.
Found a total of 1 benchmark targets for environment 'root'.
Running benchmark ~/Workspaces/python/sum-example/benchmarks/sum.py.....[1/1]
Finished benchmarking run in environment 'root'.
Starting benchmarking run in environment 'env_2'.
Discovering benchmark targets in environment 'env_2'.....done.
Found a total of 1 benchmark targets for environment 'env_2'.
Running benchmark ~/Workspaces/python/sum-example@linear-time/benchmarks/sum.py.....[1/1]
Finished benchmarking run in environment 'env_2'.
Starting benchmarking run in environment 'env_3'.
Discovering benchmark targets in environment 'env_3'.....done.
Found a total of 1 benchmark targets for environment 'env_3'.
Running benchmark ~/Workspaces/python/sum-example@constant-time/benchmarks/sum.py.....[1/1]
Finished benchmarking run in environment 'env_3'.
Finished benchmarking in all specified environments.
```

And there we have it! Instead of the manual rinse-and-repeat in a checkout
branch->benchmark->save-results kind of workflow, we obtained all the results we
need in one single command. Very nice!

## The numbers

And finally, we need to check how big our improvements actually are (or rather,
if we have achieved any in the first place!). This is handled by the
`pybm compare` command, which compares all measured results to a "frame of
reference" branch, which is taken to be the baseline for performance
comparisons. In our case, that is our fictitious math library's current
`master`.

```shell
pybm compare latest master linear-time constant-time

 Benchmark Name      | Ref           | Wall Time (usec) | CPU Time (usec) | Δt_rel (master) | Speedup      | Iterations
---------------------+---------------+------------------+-----------------+-----------------+--------------+------------
 benchmarks/sum.py:f | master        | 1346800.67       | 1358237.00      | +0.00%          | 1.00x        | 1         
 benchmarks/sum.py:f | linear-time   | 2983.11          | 2916.51         | -99.78%         | 451.48x      | 100       
 benchmarks/sum.py:f | constant-time | 0.13             | 0.12            | -100.00%        | 10759575.02x | 2000000   
```

And look here, instead of 10x-ing our previous algorithm like a normal engineer,
we actually... 10-million-x-ed it. Great work! Our constant time algorithm is
definitely ready for a pull request :-)

These are of course video game numbers, obtained by algorithmic improvements.
More common real-world examples would see improvements in the two-to-three digit
percentage range, but this example above does happen from time to time!

And with that, the first pybm tutorial is finished. I hope you enjoyed it, and
catch you on the next one!