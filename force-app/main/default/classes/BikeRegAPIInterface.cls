public with sharing class BikeRegAPIInterface {
  private static final String MDT_NAME = 'Defaults';
  private static HttpConfigWrapper cred;
  private static Boolean saveCs = false;
  private static BikeRegAPI__mdt mtd;

  private static void initiCredentials(BikeRegAPI__mdt config) {
    if (mtd == null) {
      mtd = config;
    }
    if (cred == null) {
      cred = new HttpConfigWrapper();
      if (
        cred.accessTokenExpirationDate == null ||
        cred.accessTokenExpirationDate < Datetime.now()
      ) {
        doLogin();
      }
    }
  }

  public static void getEventEntries(
    String eventId,
    String startDate,
    BikeRegAPI__mdt config
  ) {
    initiCredentials(config);
    HttpRequest req = new HttpRequest();
    req.setMethod('POST');
    req.setEndpoint(cred.baseUrl + 'EventEntries');
    req.setHeader('Content-Type', 'application/json');
    EventEntriesBody body = new EventEntriesBody(eventId);
    req.setBody(JSON.serialize(body));
    Http http = new Http();
    HttpResponse res = http.send(req);
    if (res.getStatusCode() == 200) {
      BikeRegHelper.parseEventEntries(eventId, res.getBody());
      saveAccessToken();
    }
  }

  public static void saveAccessToken() {
    if (saveCs) {
      BikeRegToken__c cs = BikeRegToken__c.getInstance();
      if (cs == null) {
        cs = new BikeRegToken__c();
      }
      cs.Value__c = cred.accessToken;
      cs.ExpirationDate__c = cred.accessTokenExpirationDate;
      upsert cs;
    }
  }

  public static void doLogin() {
    HttpRequest req = new HttpRequest();
    req.setMethod('POST');
    req.setEndpoint(cred.baseUrl + 'PromoterLogin');
    req.setHeader('Content-Type', 'application/json');
    LoginBody body = new LoginBody();
    req.setBody(JSON.serialize(body));
    Http http = new Http();
    HttpResponse res = http.send(req);
    if (res.getStatusCode() == 200) {
      PromoterLoginResultWrapper outerWrapper = (PromoterLoginResultWrapper) JSON.deserialize(
        res.getBody(),
        PromoterLoginResultWrapper.class
      );
      PromoterLoginDetails innerWrapper = (PromoterLoginDetails) JSON.deserialize(
        outerWrapper.PromoterLoginResult,
        PromoterLoginDetails.class
      );
      cred.accessToken = innerWrapper.authToken;
      cred.accessTokenExpirationDate = Datetime.now().addHours(23);
      saveCs = true;
    }
  }

  public class HttpConfigWrapper {
    String baseUrl;
    String accessToken;
    String username;
    String password;
    Datetime accessTokenExpirationDate;

    public HttpConfigWrapper() {
      if (mtd == null) {
        mtd = BikeRegAPI__mdt.getInstance(MDT_NAME);
      }
      baseUrl = mtd.BaseURL__c;
      username = mtd.Username__c;
      password = mtd.Password__c;
      BikeRegToken__c cs = BikeRegToken__c.getInstance();
      if (cs == null) {
        cs = new BikeRegToken__c();
      }
      accessToken = cs.Value__c;
      accessTokenExpirationDate = cs.ExpirationDate__c;
    }
  }

  public class LoginBody {
    public String username;
    public String password;
    public LoginBody() {
      username = cred.username;
      password = cred.password;
    }
  }

  public class PromoterLoginResultWrapper {
    public String PromoterLoginResult;
  }

  public class PromoterLoginDetails {
    public String Status;
    public String authToken;
    public String promoterID;
  }

  public class EventEntriesBody {
    public String eventID;
    public String token;

    public EventEntriesBody(String eventID) {
      this.eventID = eventID;
      this.token = cred.accessToken;
    }
  }
}