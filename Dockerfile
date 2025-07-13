FROM python:3.11-slim

# install pandoc and basic TeX packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends pandoc texlive texlive-latex-extra texlive-fonts-extra lmodern fonts-dejavu wget && \
    rm -rf /var/lib/apt/lists/*

# install OpenMoji fonts for emoji support
RUN mkdir -p /usr/share/fonts && \
    wget -O /usr/share/fonts/OpenMoji-black-glyf.ttf https://github.com/hfg-gmuend/openmoji/raw/master/font/OpenMoji-black-glyf/OpenMoji-black-glyf.ttf && \
    wget -O /usr/share/fonts/OpenMoji-color-glyf_colr_0.ttf https://github.com/hfg-gmuend/openmoji/raw/master/font/OpenMoji-color-glyf_colr_0/OpenMoji-color-glyf_colr_0.ttf && \
    fc-cache -f -v

WORKDIR /app

# copy project and install
COPY gitbook_worker/ ./gitbook_worker
RUN pip install --no-cache-dir ./gitbook_worker

ENTRYPOINT ["gitbook-worker"]
CMD ["--help"]
