.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=====================
Account Consolidation
=====================

This module extends the functionality of accounting to allow you to consolidate
journal items in a consolidation company.

Installation
============

To install this module, you need the modules `currency_monthly_rate` and
`account_reversal` to be available in your system.

Configuration
=============

To configure this module, you need to flag a company as Consolidation in the
Accounting settings.

Then, you should define a consolidation difference account and a consolidation
journal on the consolidation company, and create consolidation profiles for
each subsidiary you want to consolidate.

For each subsidiary to consolidate, make sure the related partner of the
company has no company_id defined.

Afterwards, you should define a consolidation account from your consolidation
company, on every active account of the subsidiaries.

You can then use the 'Consolidation : Checks' wizard in Accounting > Adviser to
ensure every active account of your subsidiaries are set, and company partners
have no company defined.

Make sure you also defined currency rates and monthly currency rates on the
currencies used in your subsidiaries, as P&L accounts are consolidated using
monthly rates and B.S accounts using standard 'spot' rates.

Usage
=====

To consolidate subsidiaries in your consolidation company, you should use
'Consolidation : consolidate' wizard in Accounting > Adviser.

You have to select the month until which every account move will be processed,
and select if you want to consolidate all the moves or only posted ones.

This will generate a journal entry in YTD (Year-To-Date) mode on your
consolidation company for each subsidiary. Those entries are flagged as
'to be reversed', so they will actually be reversed when you run the
consolidation the next time.

The generated journal entry is unposted, allowing you to modify or delete it to
run the consolidation again.


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/90/11.0

Known issues
============

* When saving the accounting settings, the group multi-company will be removed
  from every user if the group isn't implied by the group employes.
* Consolidation manager has access to all the settings, or he wouldn't be able
  to configure the module.

Roadmap
=======

* Implement a distinction on analytic accounts

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/account-consolidation/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://odoo-community.org/logo.png>`_.

Contributors
------------

* Guewen Baconnier <guewen.baconnier@camptocamp.com>
* Nicolas Bessi
* Vincent Renaville <vincent.renaville@camptocamp.com>
* Akim Juillerat <akim.juillerat@camptocamp.com>

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
