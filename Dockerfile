FROM 889174357220.dkr.ecr.us-west-2.amazonaws.com/deepstream:6.4-vegas

USER kwali

ENV HOME=/home/kwali

COPY --chown=kwali:kwali ./opencv_python*.whl ${HOME}

RUN python3 -m pip install ${HOME}/opencv_python*.whl

ENV WORKDIR=${HOME}/display_server

RUN mkdir -p ${WORKDIR}
COPY ./requirements.txt ${WORKDIR}/requirements.txt

WORKDIR ${WORKDIR}

RUN python3 -m pip install -r requirements.txt

ENV PATH=${PATH}:${HOME}/.local/bin

COPY . ${WORKDIR}/

ENTRYPOINT ["uvicorn", "--app-dir=src", "main:app", "--reload", "--host", "0.0.0.0"]
