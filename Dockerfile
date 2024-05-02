FROM amrit3701/freecad-cli:0.21-amd64-01.05.2024

WORKDIR /

ENV LANG=en_US.UTF-8
RUN apt-get update && apt-get install -y locales && \
    sed -i -e "s/# $LANG.*/$LANG UTF-8/" /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=$LANG
ENV LC_ALL en_US.UTF-8
ENV LANGUAGE en_US:en

COPY requirements/main.txt  .
RUN  pip3 install -r main.txt --break-system-packages

COPY fc_worker/ /fc_worker/.

ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/bin/aws-lambda-rie

COPY entry.sh lambda.py /

RUN chmod 755 /usr/bin/aws-lambda-rie /entry.sh

ENTRYPOINT [ "/entry.sh" ]

CMD [ "lambda.lambda_handler" ]
