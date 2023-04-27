FROM simonkorl0228/aitrans_build:buster as build
WORKDIR /build
# tcp build folder
COPY ./tcp/tcp_client ./tcp/tcp_client
COPY ./tcp/tcp_server ./tcp/tcp_server
COPY ./tcp/dtp_utils ./tcp/dtp_utils
COPY ./tcp/Makefile ./tcp/Makefile
RUN echo "[source.crates-io]\n\
    replace-with = 'tuna'\n\n\
    [source.tuna]\n\
    registry = \"https://mirrors.tuna.tsinghua.edu.cn/git/crates.io-index.git\"" > $CARGO_HOME/config && \
    cd tcp && make
# dtp build folder
COPY ./dtp/dtp_client ./dtp/dtp_client
COPY ./dtp/dtp_server ./dtp/dtp_server
COPY ./dtp/dtp_utils ./dtp/dtp_utils
COPY ./dtp/deps ./dtp/deps
COPY ./dtp/Makefile ./dtp/Makefile
WORKDIR /build/dtp
RUN cd dtp_server && cargo build --release
RUN cd dtp_client && cargo build --release

# just keep necessary files
FROM simonkorl0228/aitrans_image_base:buster
# copy tcp files
COPY --from=build \
    /build/tcp/tcp_server/target/release/tcp_server /home/aitrans-server/bin/tcp_server
COPY --from=build \
    /build/tcp/tcp_client/target/release/tcp_client /home/aitrans-server/tcp_client
# tcp shell
COPY ./tcp/aitrans-server/run_tcp_in_docker.sh /home/aitrans-server/tcp_run_test.sh
COPY ./tcp/aitrans-server/kill_server.sh /home/aitrans-server/kill_server.sh

# copy dtp files
COPY --from=build \
    /build/dtp/dtp_server/target/release/dtp_server /home/aitrans-server/bin/dtp_server
COPY --from=build \
    /build/dtp/dtp_client/target/release/dtp_client /home/aitrans-server/dtp_client
# dtp shell
COPY ./dtp/aitrans-server/run_dtp_in_docker.sh /home/aitrans-server/dtp_run_test.sh