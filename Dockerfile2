# Use a slim Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY ./tele_notebook ./tele_notebook

# This command will be overridden by docker-compose.yml
CMD ["python", "-m", "tele_notebook.bot.main"]


# FROM python:3.11-slim

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Add the new lines here
# COPY proxy_ca.crt /usr/local/share/ca-certificates/proxy_ca.crt
# RUN update-ca-certificates

# # Your original command to install graphviz
# RUN apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*

# # Copy the application code
# COPY ./tele_notebook ./tele_notebook

# # This command will be overridden by docker-compose.yml
# CMD ["python", "-m", "tele_notebook.bot.main"]