public class EventEntryWrapper {
  public List<GetEventEntriesResult> GetEventEntriesResult;

  public class GetEventEntriesResult {
    public UserInfo UserInfo;
    public Decimal AmountDiscounted;
    public Decimal AmtPaid;
    public String Bib;
    public String CategoryName;
    public String ConfirmationNumber;
    public String DateEntered;
    public Integer EID;
    public Decimal EntryFee;
    public Integer EntryMethod;
    public Integer EventID;
    public String LastModified;
    public Integer Quantity;

    public String GroupHeaderName;
    public Boolean HideOnWhosRegistered;
    public Boolean IsCheckedIn;
    public Boolean IsRaceDay;
    public String Notes;
    public Decimal PromoterTax;
    public String RaceID;
    public Integer RaceRecID;
    public Integer TransactionType;
    public Integer CrossResultsPoints;
    public Integer UCIPoints;
    public Integer USACCXRank;
    public String LicenseStatus;
    public Integer RankingPoints;
  }

  public class UserInfo {
    public String FirstName;
    public String MiddleName;
    public String LastName;
    public String Email;
    public String Address1;
    public String Address2;
    public String City;
    public String State;
    public String ZIP;
    public String Phone;
    public String Gender;
    public Integer DOBdd;
    public Integer DOBmm;
    public Integer DOByyyy;
    public String Team;
  }

  public static EventEntryWrapper parse(String json) {
    json = json.replace('\\"', '"');
    json = json.replace('"[{', '[{');
    json = json.replace('}]"', '}]');
    if (json.equals('{"GetEventEntriesResult":"[]"}')) {
      return null;
    } else {
      return (EventEntryWrapper) System.JSON.deserialize(
        json,
        EventEntryWrapper.class
      );
    }
  }
}