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