# python:3.12-slim, not the full python:3.12 image — the full image is
# ~1GB mostly from build tools this project never needs. psycopg2-binary,
# bcrypt, and cryptography (all in requirements.txt) ship prebuilt wheels,
# so there is no C compiler to install here, and no reason to pay for one
# in image size.
FROM python:3.12-slim

WORKDIR /app

# Copied and installed BEFORE the rest of the source. Docker caches each
# instruction as a layer — as long as requirements.txt doesn't change,
# this layer is reused on every later build, so editing a router file and
# rebuilding does not reinstall every dependency from scratch.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now the rest of the backend source.
COPY . .

# Runs as a non-root user rather than the container default (root).
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# No --reload here — that's a local-development convenience, not something
# a container running in CI or on Render should have.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]