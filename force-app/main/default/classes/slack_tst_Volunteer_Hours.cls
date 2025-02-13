@isTest
public class slack_tst_Volunteer_Hours {
    @isTest 
    static void testTrigger() {
        Campaign Camp = new Campaign(
            Name = 's'
        );
        insert Camp;

        GW_Volunteers__Volunteer_Job__c VolJob = new GW_Volunteers__Volunteer_Job__c(
            GW_Volunteers__Campaign__c = Camp.Id,
            Name = 'Job1'
        );
        insert VolJob;
        
        GW_Volunteers__Volunteer_Shift__c vol_Shift1 = new GW_Volunteers__Volunteer_Shift__c (
            GW_Volunteers__Volunteer_Job__c = VolJob.Id , 
            GW_Volunteers__Start_Date_Time__c = system.today(), 
            GW_Volunteers__Duration__c = 2.00);
        insert vol_Shift1;

        Contact Contact1 = new Contact(
            LastName = 's'
        );
        insert Contact1;
        
        GW_Volunteers__Volunteer_Hours__c VolHrs = new GW_Volunteers__Volunteer_Hours__c(
            GW_Volunteers__Contact__c = Contact1.Id,
            GW_Volunteers__Volunteer_Job__c = VolJob.Id,
            GW_Volunteers__Number_of_Volunteers__c = 1,
            GW_Volunteers__Start_Date__c = Date.today(),
            GW_Volunteers__Volunteer_Shift__c = vol_Shift1.Id , 
            GW_Volunteers__Status__c = 'Web Sign Up' 
        );

        insert VolHrs;
        
                Legal_Requirement__c LegalReq1 = new Legal_Requirement__c (
            Name='LegalReqName'
        );
        Insert LegalReq1;
        
        Legal_Document__c LegalDoc1 = new Legal_Document__c(
            Contact__c = Contact1.Id,
            Legal_Requirement__c = LegalReq1.Id
        );
        Insert LegalDoc1;
    }
}