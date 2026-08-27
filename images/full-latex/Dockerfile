FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y texlive-full
RUN apt install python3 python3-pip python3-venv -y

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install pymupdf==1.28.0

# this allowed LuaLaTeX to cache some fonts or so
# heavily speeds up simple compilations
WORKDIR /tmp
COPY test.tex .
RUN lualatex test.tex

WORKDIR /app