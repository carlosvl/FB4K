@IsTest
public class HttpMock implements HttpCalloutMock {
  private List<Mock> mocks = new List<Mock>();
  private Integer count = 0;

  public HttpResponse respond(HTTPRequest req) {
    while (count < this.mocks.size()) {
      Mock m = mocks[count];
      HttpResponse res = m.respond(req);
      if (m.end())
        count++;
      return res;
    }
    return respStatus(505);
  }

  public HttpMock addMockJson(Object o) {
    HttpResponse res = new HttpResponse();
    res.setStatusCode(200);
    res.setBody(JSON.serialize(o));
    this.mocks.add(new Mock(res));
    return this;
  }

  public HttpMock addMock(HttpResponse res) {
    this.mocks.add(new Mock(res));
    return this;
  }

  public HttpMock addMockBody(String body) {
    HttpResponse res = new HttpResponse();
    res.setStatusCode(200);
    res.setBody(body);
    this.mocks.add(new Mock(res));
    return this;
  }

  public HttpMock addMockStatus(Integer status) {
    this.mocks.add(new Mock(respStatus(status)));
    return this;
  }

  static HttpResponse respStatus(Integer status) {
    HttpResponse res = new HttpResponse();
    res.setStatusCode(status);
    return res;
  }

  public HttpRequest getRequest(Integer i) {
    if (i >= this.mocks.size())
      return null;
    return this.mocks[i].getRequest();
  }

  private virtual class Mock {
    protected HttpRequest request = null;
    protected HttpResponse response = null;

    public virtual Boolean end() {
      return request != null;
    }

    public virtual HttpRequest getRequest() {
      return request;
    }

    public Mock(HttpResponse res) {
      this.response = res;
    }

    public virtual HttpResponse respond(HTTPRequest req) {
      this.request = req;
      return this.response;
    }
  }
}