from setuptools import setup

setup(
        name='funlib.show.neuroglancer',
        version='0.1',
        url='https://github.com/funkelab/funlib.show.neuroglancer',
        author='Jan Funke',
        author_email='funkej@janelia.hhmi.org',
        license='MIT',
        install_requires=[
            'neuroglancer',
            'daisy'
        ],
        packages=[
            'funlib.show.neuroglancer'
        ],
        scripts=[
            'scripts/neuroglancer'
        ]
)
