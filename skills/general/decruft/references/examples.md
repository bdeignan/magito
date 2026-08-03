# Decruft examples

Curated from the [deslop.it pattern catalog](https://github.com/zaffnet/deslop.it/blob/main/skills/deslop/references/pattern-catalog.md)
(MIT), which documents 42 patterns across six categories with a 1.0x–1.5x weighting
scheme. This file keeps the 13 most Python-idiom-specific of those patterns and
regroups them under `decruft`'s own four buckets — dropping deslop.it's six categories
and its weights entirely. `decruft` doesn't score; it proposes a handful of high-conviction
findings. Two Test cruft examples below aren't from deslop.it — the source catalog has
no test category, so they're written here to keep that bucket real.

Every example is a `before → after` sketch, not a diff to apply verbatim: check the
surrounding code before assuming the same move fits.

## Exception cruft

**Silent swallow** — catching an exception and returning a default hides a real failure
from the caller.

```python
# Before
def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

# After
def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)
```

**Impossible except** — the `try` guards an operation that can't raise the exception
being caught, given the actual type.

```python
# Before
def get_name(user: User) -> str:
    try:
        return user.name
    except AttributeError:
        return "Unknown"

# After
def get_name(user: User) -> str:
    return user.name
```

**Unreachable guard** — `is not None` on a parameter whose type is already non-optional;
no caller can trigger the branch.

```python
# Before
def process_item(item: Item) -> str:
    if item is not None:
        return item.name
    return ""

# After
def process_item(item: Item) -> str:
    return item.name
```

**Internal validation** — type/shape checks on a private, internal-only function
re-validate what every caller already guarantees.

```python
# Before
def _compute_score(values: list[float]) -> float:
    if not isinstance(values, list):
        raise TypeError("values must be a list")
    return sum(values) / len(values)

# After
def _compute_score(values: list[float]) -> float:
    return sum(values) / len(values)
```

## Test cruft

**Mocking the seam under test** — the test mocks the exact function it claims to
verify, so the real path never runs and the suite stays green regardless.

```python
# Before
def test_process_order():
    with patch("orders.process_order", return_value=True) as mock_process:
        result = process_order(order)
    mock_process.assert_called_once()

# After
def test_process_order():
    result = process_order(order)
    assert result.status == "confirmed"
```

**Asserting implementation details** — the test pins call counts or private attributes
instead of the behavior a caller actually depends on.

```python
# Before
def test_send_email():
    sender = EmailSender()
    sender.send(msg)
    assert sender._smtp_client.sendmail.call_count == 1

# After
def test_send_email():
    sender = EmailSender()
    result = sender.send(msg)
    assert result.delivered
```

## Indirection cruft

**Transparent wrapper** — a class whose every method delegates straight through to the
wrapped object, adding no logic, error handling, or state.

```python
# Before
class DatabaseConnection:
    def __init__(self, pool: ConnectionPool):
        self._pool = pool

    def execute(self, query: str) -> Result:
        return self._pool.execute(query)

# After
pool = ConnectionPool(...)
pool.execute(query)
```

**One-caller helper** — a helper called from exactly one site earns nothing by
existing separately; inline it.

```python
# Before
def _build_header(title: str) -> str:
    return f"=== {title} ==="

def render_report(title: str, body: str) -> str:
    header = _build_header(title)
    return f"{header}\n{body}"

# After
def render_report(title: str, body: str) -> str:
    header = f"=== {title} ==="
    return f"{header}\n{body}"
```

**Once-used constant** — a module-level name used in exactly one place adds a lookup
with no reuse to justify it.

```python
# Before
BATCH_SIZE = 100

def process_items(items: list) -> None:
    for i in range(0, len(items), BATCH_SIZE):
        handle_batch(items[i:i + BATCH_SIZE])

# After
def process_items(items: list) -> None:
    batch_size = 100
    for i in range(0, len(items), batch_size):
        handle_batch(items[i:i + batch_size])
```

**Delegation chain** — A calls B calls C, and the middle layers pass arguments through
without adding logic or branching.

```python
# Before
def handle_request(request: Request) -> Response:
    return _process_request(request)

def _process_request(request: Request) -> Response:
    return _execute_request(request)

def _execute_request(request: Request) -> Response:
    return Response(data=request.body)

# After
def handle_request(request: Request) -> Response:
    return Response(data=request.body)
```

## Flow cruft

**Deep nesting instead of guard clauses** — nested `if`s bury the real logic three
levels deep when early returns would flatten it to one.

```python
# Before
def process(data: dict | None) -> str:
    if data is not None:
        if "key" in data:
            value = data["key"]
            if isinstance(value, str):
                return value.strip()
    return ""

# After
def process(data: dict | None) -> str:
    if data is None:
        return ""
    if "key" not in data:
        return ""
    value = data["key"]
    if not isinstance(value, str):
        return ""
    return value.strip()
```

**Manual list build** — a loop that only appends is a list comprehension wearing more
lines.

```python
# Before
def get_names(users: list[User]) -> list[str]:
    names = []
    for user in users:
        names.append(user.name)
    return names

# After
def get_names(users: list[User]) -> list[str]:
    return [user.name for user in users]
```

**String concatenation chain** — repeated `+=` on a string is harder to read than one
f-string, and slower.

```python
# Before
def build_message(name: str, count: int) -> str:
    message = "Hello, " + name + ". "
    message += "You have " + str(count) + " items. "
    message += "Thank you."
    return message

# After
def build_message(name: str, count: int) -> str:
    return f"Hello, {name}. You have {count} items. Thank you."
```

**Explicit length check** — `len(x) == 0` / `len(x) > 0` says the same thing as
truthiness, at more words.

```python
# Before
if len(items) == 0:
    return "No items"

# After
if not items:
    return "No items"
```

**Restating comment** — a comment that repeats exactly what the next line already
says adds a second thing to keep in sync, not information.

```python
# Before
# Increment the counter by one
counter += 1

# After
counter += 1
```
