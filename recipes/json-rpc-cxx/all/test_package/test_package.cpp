#include <jsonrpccxx/client.hpp>
#include <jsonrpccxx/server.hpp>

#include <iostream>
#include <string>

// Routes client requests straight into the server, as upstream's examples do.
class InMemoryConnector : public jsonrpccxx::IClientConnector
{
public:
  explicit InMemoryConnector(jsonrpccxx::JsonRpcServer& server) : server(server) {}
  std::string Send(const std::string& request) override { return server.HandleRequest(request); }

private:
  jsonrpccxx::JsonRpcServer& server;
};

int add(int a, int b) { return a + b; }

int main()
{
  jsonrpccxx::JsonRpc2Server server;
  server.Add("add", jsonrpccxx::GetHandle(&add), {"a", "b"});

  InMemoryConnector connector(server);
  jsonrpccxx::JsonRpcClient client(connector, jsonrpccxx::version::v2);
  const int sum = client.CallMethod<int>(1, "add", {2, 3});
  std::cout << "add(2, 3) = " << sum << std::endl;

  try {
    client.CallMethod<int>(2, "missing", {});
    return 1;
  } catch (const jsonrpccxx::JsonRpcException& e) {
    std::cout << "missing: " << e.what() << std::endl;
  }
  return sum == 5 ? 0 : 1;
}
