import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-account-consolidation",
    description="Meta package for oca-account-consolidation Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-account_consolidation_oca',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
