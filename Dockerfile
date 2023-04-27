FROM simonkorl0228/aitrans_build:buster as build
WORKDIR /build
COPY ./tcp/tcp_client ./tcp/tcp_client
COPY ./tcp/tcp_server ./tcp/tcp_server
COPY ./tcp/dtp_utils ./tcp/dtp_utils
COPY ./tcp/Makefile ./tcp/Makefile
RUN echo "[source.crates-io]\n\
    replace-with = 'tuna'\n\n\
    [source.tuna]\n\
    registry = \"https://mirrors.tuna.tsinghua.edu.cn/git/crates.io-index.git\"" > $CARGO_HOME/config && \
    cd tcp && make

FROM simonkorl0228/aitrans_image_base:buster
COPY --from=build \
    /build/tcp/tcp_server/target/release/tcp_server /home/aitrans-server/tcp/bin/tcp_server
COPY --from=build \
    /build/tcp/tcp_client/target/release/tcp_client /home/aitrans-server/tcp/bin/tcp_client