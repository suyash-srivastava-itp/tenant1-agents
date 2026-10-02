"""Arithmetic tools for the reference tenant.

A tenant tool imports the decorators by absolute path and nothing else from
NeuroStack - `modular_agents` does not exist in the runtime image. Compare the
catalog's tools, 16 of which import `..core.tool_config` or `..core.logger` and
therefore cannot run here at all.
"""

from registry import tool_category, tool_tags


@tool_category("Arithmetic")
@tool_tags("math", "addition")
def add_numbers(left: int, right: int) -> dict:
    """Add two integers together.

    Args:
        left: The first number.
        right: The second number.
    """
    return {
        "success": True,
        "message": f"{left} + {right} = {left + right}",
        "data": {"total": left + right},
    }


@tool_category("Arithmetic")
@tool_tags("math", "primes")
def count_primes(limit: int) -> dict:
    """Count the prime numbers below a limit.

    Args:
        limit: Exclusive upper bound to count primes below.
    """
    if limit < 2:
        return {"success": True, "message": "no primes below 2", "data": {"primes": []}}

    sieve = [True] * limit
    sieve[0] = sieve[1] = False
    for candidate in range(2, int(limit**0.5) + 1):
        if sieve[candidate]:
            for multiple in range(candidate * candidate, limit, candidate):
                sieve[multiple] = False

    primes = [n for n, is_prime in enumerate(sieve) if is_prime]
    return {
        "success": True,
        "message": f"found {len(primes)} prime(s) below {limit}",
        "data": {"count": len(primes), "primes": primes[:50]},
    }
