FROM cybench/kali-linux-large:latest

COPY packages.list /tmp/packages.list

# Install common tools, Python 3.9, and Docker
RUN apt-get update && apt-get install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    liblzma-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install new Kali GPG key as per https://www.kali.org/blog/new-kali-archive-signing-key/
RUN wget https://archive.kali.org/archive-keyring.gpg -O /usr/share/keyrings/kali-archive-keyring.gpg

# Update apt lists again after adding the new key
RUN apt-get update && \
    apt-get install -f && \
    xargs -a /tmp/packages.list apt-get install -y --no-install-recommends && \
    wget https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz && \
    tar xzf Python-3.9.7.tgz && \
    cd Python-3.9.7 && \
    ./configure --enable-optimizations && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.9.7 Python-3.9.7.tgz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

WORKDIR /app

RUN ln -sf /usr/local/bin/python3.9 /usr/bin/python3 && \
    ln -sf /usr/local/bin/pip3.9 /usr/bin/pip3 && \
    python3.9 -m venv /venv

ENV PATH="/venv/bin:$PATH"

COPY ./tools/entrypoint.sh /usr/local/bin/

COPY bountytasks/requirements.sh /bountytasks/requirements.sh
COPY bountytasks/requirements.txt /bountytasks/requirements.txt

RUN chmod +x /bountytasks/requirements.sh
RUN /bountytasks/requirements.sh
RUN /venv/bin/pip install --upgrade pip
RUN /venv/bin/pip install wheel && /venv/bin/pip install -r /bountytasks/requirements.txt
