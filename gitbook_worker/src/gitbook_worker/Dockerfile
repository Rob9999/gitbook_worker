FROM pandoc/latex:latest

# install fonts
RUN apk add --no-cache font-dejavu
RUN mkdir -p /usr/share/fonts
RUN wget -O /usr/share/fonts/OpenMoji-black-glyf.ttf https://github.com/hfg-gmuend/openmoji/raw/master/font/OpenMoji-black-glyf/OpenMoji-black-glyf.ttf && \
    fc-cache -f -v
RUN wget -O /usr/share/fonts/OpenMoji-color-glyf_colr_0.ttf https://github.com/hfg-gmuend/openmoji/raw/master/font/OpenMoji-color-glyf_colr_0/OpenMoji-color-glyf_colr_0.ttf && \
    fc-cache -f -v
RUN fc-cache -f -v

# Update TeXLive und installiere pdflscape und ltablex
RUN tlmgr update --self --all && tlmgr install pdflscape ltablex tabularx

WORKDIR /data
