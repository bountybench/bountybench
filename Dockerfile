FROM cybench/kali-linux-large:latest

COPY packages.list /tmp/packages.list

# Install common tools, Python 3.9, and Docker
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

COPY bountybench/requirements.sh /bountybench/requirements.sh
COPY bountybench/requirements.txt /bountybench/requirements.txt

RUN chmod +x /bountybench/requirements.sh
RUN /bountybench/requirements.sh
RUN /venv/bin/pip install --upgrade pip
RUN /venv/bin/pip install wheel && /venv/bin/pip install -r /bountybench/requirements.txt
