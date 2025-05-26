FROM python

USER root

WORKDIR /home/mcp

RUN apt-get update
RUN apt-get install -y python3-dev libxml2-dev libxslt1-dev gcc

COPY  . .
RUN pip install -e .

EXPOSE 3000

CMD ["python", "dracor_mcp.py"]