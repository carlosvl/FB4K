@isTest
public class slack_tst_Legal_Document {
	@isTest 
	static void testTrigger() {
		Legal_Requirement__c obj2 = new Legal_Requirement__c(
        name ='LRName');
		insert obj2;

		Contact obj1 = new Contact(
			LastName = 's'
		);
		insert obj1;

		Legal_Document__c obj0 = new Legal_Document__c(
			Contact__c = obj1.Id,
			Legal_Requirement__c = obj2.Id
		);
		insert obj0;
	}
}