############################
Account Consolidated Invoice
############################

Description
###########

This module allows organizations with multiples companies to transfer the
liability of a customer to another company and provide the customer with a
unique consolidated invoice to pay.

--------
Workflow
--------

Company 1 - Create and validate invoice
---------------------------------------

::

 A/R (partner:customer)       100 (R1)
 Sales                                      100


Company 2 - Create and validate invoice
---------------------------------------

::

 A/R  (partner:customer)      121 (R2)
 Sales                                      121

Company 3 - Create consolidated invoice
---------------------------------------

Nothing happens but selection of company1 and company2 invoices

Company 3 - Validate consolidated invoice
-----------------------------------------

Payment of company1's invoice - In company 1 using due from payment method

::

 A/R  (partner:customer)                                            100 (R1)
 A/R due from company 3                            100

Payment of company2's invoice) - In company 2 using due from payment method

::

 A/R  (partner:customer)                                            121 (R2)
 A/R due from company 3                            121

Create manual journal entry in company 3

::

 A/R due to   (partner: company1)                         100
 A/R due to   (partner: company2)                         121
 A/R  (partner:customer)           221 (Partial R3)

----------------
Customer payment
----------------

Payment (3rd company)
---------------------

::

 Bank                              100
 A/R  (partner:customer)                                 100 (Partial R3)

Configuration
=============

For each company, we need the following configuration on the company record:

* Intercompany Due From account
* Intercompany Due To account
* Intercompany Payment Method

Usage
=====

* Create invoices for the same customer in different children companies
* Create a consolidated invoice in the parent company for this customer. Make sure you select a period wide enough to include the invoices of the children company
* Validate the consolidated invoice:

  * The customer invoices in the children companies are paid.
  * The total amount is transferred in the AR account of the parent company
* Register the customer payment as usual


Credits
=======

* Open Source Integrators <https://www.opensourceintegrators.com>
* Serpent Consulting Services Pvt Ltd <https://www.serpentcs.com>

Contributors
------------

* Balaji Kannan <bkannan@opensourceintegrators.com>
* Swapnesh Shah <swapnesh.shah@serpentcs.com>
* Wolfgang Hall <whall@opensourceintegrators.com>
* Maxime Chambreuil <mchambreuil@opensourceintegrators.com>
